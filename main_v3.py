import os
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from peft import PeftModel, PeftConfig
from langdetect import detect
import logging
from fastapi.concurrency import run_in_threadpool
from contextlib import asynccontextmanager

# Настройка зеркала Hugging Face (можно переопределить через переменную окружения)
HF_MIRROR = os.getenv('HF_ENDPOINT', 'https://hf-mirror.com')
if HF_MIRROR != 'https://huggingface.co':
    os.environ['HF_ENDPOINT'] = HF_MIRROR
    print(f"Using Hugging Face mirror: {HF_MIRROR}")

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

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str
    message: str

class TranslationServer:
    def __init__(self):
        """Инициализация сервера перевода"""
        self.model = None
        self.tokenizer = None
        self.device = None
        self.model_loaded = False
        self.model_name = 'facebook/m2m100_418m'
        self.peft_model_path = "./checkpoint-3900"
        
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

    def _check_model_availability(self):
        """Проверка доступности модели в кэше"""
        cache_dir = os.path.expanduser("~/.cache/huggingface/transformers")
        model_cache_dir = os.path.join(cache_dir, f"models--facebook--m2m100_418m")
        
        if os.path.exists(model_cache_dir):
            logger.info(f"Model cache found at: {model_cache_dir}")
            return True
        else:
            logger.warning("Model not found in cache. Please run download_model.py first.")
            return False

    def _check_peft_config(self):
        """Проверка конфигурации PEFT модели"""
        try:
            if not os.path.exists(self.peft_model_path):
                logger.error(f"PEFT checkpoint directory not found: {self.peft_model_path}")
                return False
                
            config_path = os.path.join(self.peft_model_path, "adapter_config.json")
            if not os.path.exists(config_path):
                logger.error(f"PEFT config not found: {config_path}")
                return False
                
            peft_config = PeftConfig.from_pretrained(self.peft_model_path)
            logger.info(f"PEFT base model: {peft_config.base_model_name_or_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking PEFT config: {e}")
            return False

    async def initialize_model(self):
        """Асинхронная инициализация модели"""
        try:
            logger.info("Starting model initialization...")
            
            # Проверка доступности модели
            if not self._check_model_availability():
                raise RuntimeError("Model not available in cache. Run download_model.py first.")
            
            # Проверка PEFT конфигурации
            if not self._check_peft_config():
                raise RuntimeError("PEFT configuration check failed.")
            
            # Инициализация устройства
            self.device = self._initialize_device()
            
            def _load_model():
                """Блокирующая загрузка модели"""
                logger.info(f"Loading model {self.model_name}...")
                
                # Загружаем конфиг LoRA
                peft_config = PeftConfig.from_pretrained(self.peft_model_path)
                
                # Загружаем базовую модель
                base_model = M2M100ForConditionalGeneration.from_pretrained(
                    peft_config.base_model_name_or_path,
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True
                )
                
                # Подключаем LoRA-адаптер
                model = PeftModel.from_pretrained(base_model, self.peft_model_path)
                
                # Загружаем токенизатор
                tokenizer = M2M100Tokenizer.from_pretrained(peft_config.base_model_name_or_path)
                
                return model, tokenizer
            
            # Выполняем блокирующую загрузку в отдельном потоке
            self.model, self.tokenizer = await run_in_threadpool(_load_model)
            
            # Перемещение модели на устройство
            try:
                self.model = self.model.to(self.device)
                logger.info(f"Model loaded successfully. Using device: {self.device}")
            except Exception as e:
                logger.warning(f"Failed to move model to {self.device}: {e}")
                logger.info("Falling back to CPU...")
                self.device = torch.device('cpu')
                self.model = self.model.to(self.device)
                logger.info(f"Model loaded successfully on fallback device: {self.device}")
            
            self.model_loaded = True
            logger.info("Model initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"Model initialization failed: {e}")
            self.model_loaded = False
            raise
    
    def detect_language(self, text: str) -> str:
        """Определение языка текста"""
        try:
            return detect(text)
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            raise HTTPException(status_code=400, detail="Не удалось определить язык текста")
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Выполнение перевода текста"""
        if not self.model_loaded:
            raise HTTPException(status_code=503, detail="Модель не загружена. Сервер не готов к работе.")
        
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

# Глобальный экземпляр сервера
translation_server = TranslationServer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info("Application startup: Initializing model...")
    try:
        await translation_server.initialize_model()
        logger.info("Application startup completed successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize model during startup: {e}")
        logger.error("Server will start but translation endpoints will return 503 errors")
    
    yield
    
    # Shutdown
    logger.info("Application shutdown: Cleaning up...")
    if translation_server.model is not None:
        del translation_server.model
        del translation_server.tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Model cleanup completed")

# Создание приложения FastAPI с управлением жизненным циклом
app = FastAPI(
    title="AI-Translate-HUB Server",
    description="Translation server with M2M100 model and LoRA adapters",
    version="3.0.0",
    lifespan=lifespan
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка состояния сервера и готовности модели"""
    return HealthResponse(
        status="healthy" if translation_server.model_loaded else "starting",
        model_loaded=translation_server.model_loaded,
        device=str(translation_server.device) if translation_server.device else "unknown",
        message="Translation service is ready" if translation_server.model_loaded else "Model is loading or failed to load"
    )

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
        
        if not translation_server.model_loaded:
            raise HTTPException(status_code=503, detail="Модель не загружена. Попробуйте позже.")
            
        source_lang = request.source_lang
        if not source_lang:
            # Запускаем определение языка в пуле потоков
            source_lang = await run_in_threadpool(translation_server.detect_language, request.text)
            logger.info(f"Detected source language: {source_lang}")
            
        # Запускаем инференс модели в пуле потоков
        translated_text = await run_in_threadpool(
            translation_server.translate,
            request.text,
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

@app.get("/")
async def root():
    """Корневой эндпоинт с информацией о сервисе"""
    return {
        "service": "AI-Translate-HUB Server",
        "version": "3.0.0",
        "status": "running",
        "model_loaded": translation_server.model_loaded,
        "endpoints": {
            "health": "/health",
            "translate": "/model_translate",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    print("AI-Translate-HUB Server v3.0")
    print("=" * 40)
    print(f"Using Hugging Face endpoint: {HF_MIRROR}")
    print("Starting server...")
    
    # Запускаем сервер uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=5999,
        log_level="info"
    )
