import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from langdetect import detect
from peft import PeftModel, PeftConfig
import logging

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
                # Проверяем, поддерживает ли MPS нужные операции
                test_tensor = torch.tensor([1.0], device='mps')
                # Создаем тестовый placeholder для проверки
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
        
        # self.tokenizer = M2M100Tokenizer.from_pretrained(self.model_name)
        # self.model = M2M100ForConditionalGeneration.from_pretrained(self.model_name)

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
        
        # Определяем и инициализируем устройство с проверками
        self.device = self._initialize_device()
        
        # Перемещаем модель на выбранное устройство
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
            # Установка языка источника
            self.tokenizer.src_lang = source_lang
            
            # Токенизация входного текста
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
            
            # Генерация перевода
            generated_tokens = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.get_lang_id(target_lang)
            )
            
            # Декодирование результата
            translated_text = self.tokenizer.batch_decode(
                generated_tokens,
                skip_special_tokens=True
            )[0]
            
            return translated_text
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка перевода: {str(e)}")

app = FastAPI(title="Translation Server")
translation_server = TranslationServer()

@app.post("/model_translate")
async def translate(request: TranslationRequest):
    """
    Эндпоинт для перевода текста.
    
    Принимает JSON с полями:
    - text: текст для перевода
    - source_lang: исходный язык (опционально)
    - target_lang: целевой язык
    
    Возвращает JSON с результатом перевода или описанием ошибки
    """
    try:
        # Проверяем наличие обязательных полей
        if not request.text:
            raise HTTPException(status_code=400, detail="Не предоставлен текст для перевода")
        if not request.target_lang:
            raise HTTPException(status_code=400, detail="Не указан целевой язык перевода")
            
        # Определяем язык если не указан
        source_lang = request.source_lang
        if not source_lang:
            source_lang = translation_server.detect_language(request.text)
            logger.info(f"Detected source language: {source_lang}")
            
        # Выполняем перевод
        translated_text = translation_server.translate(
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5999)
