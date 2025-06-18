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
        else:
            logger.info("No GPU acceleration available, using CPU")
            return torch.device('cpu')

    def __init__(self):
        """Инициализация модели M2M100 для перевода"""
        self.model_name = 'facebook/m2m100_418m'
        logger.info(f"Loading model {self.model_name}...")

        # Путь к директории с LoRA-чекпоинтом
        peft_model_path = "best"  # TODO Добавить путь лдо весов модели

        # Загружаем конфиг LoRA
        peft_config = PeftConfig.from_pretrained(peft_model_path)
        print(peft_config.base_model_name_or_path)
        # Загружаем базовую модель
        base_model = M2M100ForConditionalGeneration.from_pretrained(peft_config.base_model_name_or_path)

        # Подключаем LoRA-адаптер
        self.model = PeftModel.from_pretrained(base_model, peft_model_path)

        # Загружаем токенизатор (тот же, что и у базовой модели)
        self.tokenizer = M2M100Tokenizer.from_pretrained(peft_config.base_model_name_or_path)
        
        self.device = self._initialize_device()
        
        try:
            self.model = self.model.to(self.device)
            logger.info(f"Model loaded successfully. Using device: {self.device}")
        except Exception as e:
            logger.warning(f"Failed to move model to {self.device}: {e}")
            logger.info("Falling back to CPU...")
            self.device = torch.device('cpu')
            self.model = self.model.to(self.device)
            logger.info(f"Model loaded successfully on fallback device: {self.device}")
    
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