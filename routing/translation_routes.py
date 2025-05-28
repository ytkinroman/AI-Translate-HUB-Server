import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from . import active_connections

from config import (
    TRANSLATION_QUEUE
)

# Настройка логирования
logger = logging.getLogger(__name__)

router = APIRouter()

class TranslationPayload(BaseModel):
    """
    Модель данных для запроса на перевод.

    Атрибуты:
        text: Текст для перевода
        translator_code: Код переводчика (yandex/google/deepl)
        target_lang: Целевой язык перевода
        source_lang: Исходный язык текста (опционально)
    """
    text: str
    translator_code: str
    target_lang: str
    source_lang: str = None

class TranslationRequest(BaseModel):
    """
    Модель запроса на перевод.

    Атрибуты:
        method: Метод запроса (обычно "translate")
        payload: Данные для перевода
        ws_session_id: ID WebSocket сессии
    """
    method: str
    payload: TranslationPayload
    ws_session_id: str



@router.post("/api/v1/translate")
async def translate_text(request: TranslationRequest):
    """
    Эндпоинт для приема запросов на перевод.

    Args:
        request: Модель запроса на перевод

    Returns:
        dict: Статус обработки запроса
    """
    try:        
        if request.method == "error":
            raise Exception("Test Error")

        
        return JSONResponse(
            status_code=status.HTTP_200_OK, 
            content={"result":{"status": "success", "text": "Запрос на перевод принят", "source_lang": "ru"}, "error": ""}
        )
    except Exception as e:
        logger.error(f"Ошибка в translate_text: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            content={"result":{"status": "false", "text": "", "source_lang": ""}, "error": str(e)}
        )