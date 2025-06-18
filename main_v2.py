import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from peft import PeftModel, PeftConfig
from langdetect import detect
import logging
# --- ИЗМЕНЕНИЕ 1: Импортируем утилиту для запуска блокирующих задач в потоке ---
from fastapi.concurrency import run_in_threadpool

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranslationRequest(BaseModel):
    text: str
    source_lang: str | None = None
    target_lang: str

class TranslationServer:
    def _initialize_device(self):
        """Инициализация устройства с проверками совместимости"""
        if torch.cuda.is_available():
            logger.info("CUDA is available, using GPU")
            return torch.device('cuda')
        elif torch.backends.mps.is_available():
            try:
                test_tensor = torch.tensor([1.0], device='mps')
                test_tensor = test_tensor * 2
                logger.info("MPS is available and compatible, using MPS")
                return torch.device('mps')
            except Exception as e:
                logger.warning(f"MPS is available but not compatible: {e}")
                logger.info("Falling back to CPU")
                return torch.device('cpu')
        
        logger.info("No GPU acceleration available, using CPU")
        return torch.device('cpu')

    def _load_model_with_retry(self, model_name_or_path, max_retries=3):
        """Загрузка модели с retry-логикой и оптимизациями"""
        import time
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Loading attempt {attempt + 1}/{max_retries} for {model_name_or_path}")
                
                # Сначала пробуем загрузить из кеша
                try:
                    logger.info("Attempting to load from cache (local_files_only=True)...")
                    model = M2M100ForConditionalGeneration.from_pretrained(
                        model_name_or_path,
                        local_files_only=True,  # Только из кеша
                        low_cpu_mem_usage=True,  # Оптимизация памяти
                        torch_dtype=torch.float32,  # Явный тип данных
                    )
                    logger.info("✓ Model loaded successfully from cache!")
                    return model
                    
                except Exception as cache_error:
                    logger.warning(f"Cache loading failed: {cache_error}")
                    logger.info("Falling back to online loading...")
                    
                    # Если кеш не работает, загружаем из интернета с оптимизациями
                    model = M2M100ForConditionalGeneration.from_pretrained(
                        model_name_or_path,
                        low_cpu_mem_usage=True,
                        torch_dtype=torch.float32,
                        resume_download=True,  # Возобновить прерванную загрузку
                        force_download=False,  # Не перезагружать если есть в кеше
                    )
                    logger.info("✓ Model loaded successfully from online!")
                    return model
                    
            except Exception as e:
                logger.error(f"Loading attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    delay = 5 * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries} loading attempts failed!")
                    raise

    def _load_tokenizer_with_retry(self, model_name_or_path, max_retries=3):
        """Загрузка токенизатора с retry-логикой"""
        import time
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Loading tokenizer attempt {attempt + 1}/{max_retries}")
                
                # Пробуем загрузить из кеша
                try:
                    tokenizer = M2M100Tokenizer.from_pretrained(
                        model_name_or_path,
                        local_files_only=True
                    )
                    logger.info("✓ Tokenizer loaded from cache!")
                    return tokenizer
                except:
                    # Загружаем из интернета
                    tokenizer = M2M100Tokenizer.from_pretrained(model_name_or_path)
                    logger.info("✓ Tokenizer loaded from online!")
                    return tokenizer
                    
            except Exception as e:
                logger.error(f"Tokenizer loading attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    delay = 2 * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise

    def __init__(self):
        """Инициализация модели M2M100 для перевода"""
        self.model_name = 'facebook/m2m100_418m'
        logger.info(f"=== Starting model initialization: {self.model_name} ===")
        
        try:
            # Путь к директории с LoRA-чекпоинтом
            peft_model_path = "./checkpoint-3900"
            logger.info(f"PEFT model path: {peft_model_path}")

            # Загружаем конфиг LoRA
            logger.info("Loading PEFT config...")
            peft_config = PeftConfig.from_pretrained(peft_model_path)
            base_model_name = peft_config.base_model_name_or_path
            logger.info(f"Base model from PEFT config: {base_model_name}")

            # Загружаем базовую модель с retry-логикой
            logger.info("Loading base model...")
            base_model = self._load_model_with_retry(base_model_name)

            # Подключаем LoRA-адаптер
            logger.info("Loading PEFT adapter...")
            self.model = PeftModel.from_pretrained(base_model, peft_model_path)
            logger.info("✓ PEFT adapter loaded successfully!")

            # Загружаем токенизатор
            logger.info("Loading tokenizer...")
            self.tokenizer = self._load_tokenizer_with_retry(base_model_name)
            
            # Определяем и инициализируем устройство с проверками
            logger.info("Initializing device...")
            self.device = self._initialize_device()
            
            # Перемещаем модель на выбранное устройство
            logger.info(f"Moving model to device: {self.device}")
            try:
                self.model = self.model.to(self.device)
                logger.info(f"✓ Model loaded successfully. Using device: {self.device}")
            except Exception as e:
                logger.warning(f"Failed to move model to {self.device}: {e}")
                logger.info("Falling back to CPU...")
                self.device = torch.device('cpu')
                self.model = self.model.to(self.device)
                logger.info(f"✓ Model loaded successfully on fallback device: {self.device}")
                
            logger.info("=== Model initialization completed successfully! ===")
            
        except Exception as e:
            logger.error(f"Critical error during model initialization: {e}")
            logger.error("Please check your internet connection and try again")
            raise RuntimeError(f"Failed to initialize translation model: {e}")
    
    def detect_language(self, text: str) -> str:
        """Определение языка текста"""
        try:
            return detect(text)
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            raise HTTPException(status_code=400, detail="Не удалось определить язык текста")
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Выполнение перевода текста"""
        try:
            self.tokenizer.src_lang = source_lang
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
            generated_tokens = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.get_lang_id(target_lang)
            )
            translated_text = self.tokenizer.batch_decode(
                generated_tokens,
                skip_special_tokens=True
            )[0]
            return translated_text
        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка перевода: {str(e)}")

# Модель инициализируется один раз при старте приложения. Это правильно.
app = FastAPI(title="Translation Server")
translation_server = TranslationServer()

@app.post("/model_translate")
async def translate(request: TranslationRequest):
    """
    Эндпоинт для перевода текста.
    Блокирующие вызовы вынесены в `run_in_threadpool` для предотвращения
    блокировки основного потока сервера.
    """
    try:
        if not request.text:
            raise HTTPException(status_code=400, detail="Не предоставлен текст для перевода")
        if not request.target_lang:
            raise HTTPException(status_code=400, detail="Не указан целевой язык перевода")
            
        source_lang = request.source_lang
        if not source_lang:
            # --- ИЗМЕНЕНИЕ 2: Запускаем определение языка в пуле потоков ---
            # Это тоже блокирующая операция, ее стоит вынести из основного потока.
            source_lang = await run_in_threadpool(translation_server.detect_language, request.text)
            logger.info(f"Detected source language: {source_lang}")
            
        # --- ИЗМЕНЕНИЕ 3: Запускаем инференс модели в пуле потоков ---
        # Это главная блокирующая операция. `await` дождется результата, 
        # но не будет блокировать сервер от приема других запросов.
        translated_text = await run_in_threadpool(
            translation_server.translate, # Функция
            request.text,                 # Позиционные аргументы для функции
            source_lang,
            request.target_lang
        )
        
        return {
            "result": {
                "success": True,
                "text": translated_text,
                "source_language": source_lang
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Запускаем сервер uvicorn. Он по умолчанию использует один рабочий процесс (worker),
    # что идеально для нашего подхода с run_in_threadpool.
    uvicorn.run(app, host="0.0.0.0", port=5999)
