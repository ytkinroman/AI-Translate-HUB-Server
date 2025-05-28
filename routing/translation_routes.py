import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from transport.rabbitmq.MessageSender import MessageSender
from transport.redis.redis_client import check_connection
from . import active_connections

from config import (
    TRANSLATION_QUEUE
)

# Настройка логирования
logger = logging.getLogger(__name__)

router = APIRouter()
message_sender = MessageSender()

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

class TranslationRequestResult(BaseModel):
    """
    Модель результата запроса на перевод.

    Атрибуты:
        status: Статус обработки запроса
        message: Сообщение о статусе
    """
    status: str
    message: str

class TranslationResult(BaseModel):
    """
    Модель результата перевода.

    Атрибуты:
        connection_id: ID соединения для отправки результата
        result: Словарь с результатом перевода
    """
    connection_id: str
    result: dict
    error: str = None

@router.post("/api/v1/translate", response_model=TranslationRequestResult)
async def translate_text(request: TranslationRequest):
    """
    Эндпоинт для приема запросов на перевод.

    Args:
        request: Модель запроса на перевод

    Returns:
        dict: Статус обработки запроса
    """
    try:        
        # Проверяем, существует ли сессия
        if not check_connection(request.ws_session_id):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                content={"status": "error", "message": "Недействительный ID сессии"}
            )
            
        # Отправляем запрос через MessageSender
        await message_sender.send_message(
            {
                "payload": request.payload.dict(),
                "method": request.method,
                "ws_session_id": request.ws_session_id,
                "queue": TRANSLATION_QUEUE
            }
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK, 
            content={"status": "success", "message": "Запрос на перевод принят"}
        )
    except Exception as e:
        logger.error(f"Ошибка в translate_text: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            content={"status": "error", "message": str(e)}
        )

@router.post("/translation-result")
async def handle_translation_result(result: TranslationResult):
    """
    Принимает результат перевода и отправляет его клиенту через WebSocket.

    Args:
        result: Модель результата перевода

    Returns:
        dict: Статус отправки результата

    Raises:
        HTTPException: Если соединение не найдено или произошла ошибка
    """
    try:
        connection_id = result.connection_id
        
        # Проверяем существование соединения
        if not check_connection(connection_id):
            raise HTTPException(status_code=404, detail="Соединение не найдено")
            
        # Получаем WebSocket из активных соединений
        websocket = active_connections.get(connection_id)
        if not websocket:
            raise HTTPException(status_code=404, detail="WebSocket соединение не найдено")
            
        # Отправляем результат клиенту
        await websocket.send_json({
            "connection_id": connection_id, 
            "result": result.result, 
            "error": result.error
        })
        return {"status": "success", "message": "Результат отправлен клиенту"}
        
    except Exception as e:
        logger.error(f"Ошибка при отправке результата перевода: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
