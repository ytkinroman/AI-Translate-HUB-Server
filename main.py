import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from langdetect import detect
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
    def __init__(self):
        """Инициализация модели M2M100 для перевода"""
        self.model_name = 'facebook/m2m100_418m'
        logger.info(f"Loading model {self.model_name}...")
        
        self.tokenizer = M2M100Tokenizer.from_pretrained(self.model_name)
        self.model = M2M100ForConditionalGeneration.from_pretrained(self.model_name)
        
        # Перемещаем модель на GPU если доступно
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        logger.info(f"Model loaded successfully. Using device: {self.device}")
    
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
