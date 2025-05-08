import uuid
import time
import logging
from typing import Dict
from pydantic import BaseModel
from asyncio import create_task, sleep
from fastapi.middleware.cors import CORSMiddleware
from transport.rabbitmq.MessageSender import MessageSender
from transport.redis.redis_client import store_connection, remove_connection, check_connection
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException

from config import (
    LOG_LEVEL, 
    LOG_FORMAT,
    CORS_ORIGINS,
    WS_PING_TIMEOUT,
    MAX_CONNECTIONS,
    WS_PING_INTERVAL,
    TRANSLATION_QUEUE
)

"""
Основной модуль FastAPI приложения.

Обеспечивает:
- WebSocket подключения для real-time коммуникации
- HTTP endpoints для получения запросов на перевод
- Обработку результатов перевода
- Мониторинг активных соединений
- Механизм проверки активности соединений (ping/pong)
"""

# Словарь для хранения активных WebSocket соединений
active_connections: Dict[str, WebSocket] = {}

# Настройка логирования
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

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

class TranslationResult(BaseModel):
    """
    Модель результата перевода.

    Атрибуты:
        connection_id: ID соединения для отправки результата
        result: Словарь с результатом перевода
    """
    connection_id: str
    result: dict

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/translate")
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
            return {"status": "error", "message": "Недействительный ID сессии"}
            
        # Отправляем запрос через MessageSender
        await message_sender.send_message(
            {
                "payload": request.payload.dict(),
                "method": request.method,
                "ws_session_id": request.ws_session_id,
                "queue": TRANSLATION_QUEUE
            }
        )
        return {"status": "success", "message": "Запрос на перевод принят"}
    except Exception as e:
        logger.error(f"Ошибка в translate_text: {str(e)}")
        return {"status": "error", "message": str(e)}

async def ping_connection(websocket: WebSocket, session_id: str):
    """
    Асинхронная функция для периодической проверки активности WebSocket соединения.
    
    Args:
        websocket: Активное WebSocket соединение для проверки
        session_id: Уникальный идентификатор сессии для логирования

    Механизм работы:
        - Отправляет ping-сообщение каждые WS_PING_INTERVAL секунд
        - Если ответ не получен в течение WS_PING_TIMEOUT секунд, соединение закрывается
        - Логирует все ошибки и таймауты для отладки
    """
    while True:
        try:
            await sleep(WS_PING_INTERVAL)
            ping_start = time.time()
            
            # Отправляем heartbeat сообщение
            await websocket.send_json({"type": "ping"})
            
            # Ждем ответ не более WS_PING_TIMEOUT секунд
            try:
                data = await websocket.receive_json()
                if data.get("type") != "pong":
                    continue
            except Exception as e:
                logger.warning(f"Не получен pong ответ для сессии {session_id}: {str(e)}")
                await websocket.close(code=1001)  # Going away
                break
                
            # Проверяем таймаут
            if time.time() - ping_start > WS_PING_TIMEOUT:
                logger.warning(f"WebSocket таймаут для сессии {session_id}")
                await websocket.close(code=1001)  # Going away
                break
                
        except Exception as e:
            logger.error(f"Ошибка при пинге для сессии {session_id}: {str(e)}")
            break

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint для установки и поддержания WebSocket соединения.
    
    Args:
        websocket: Входящее WebSocket соединение

    Функциональность:
        1. Проверяет лимит подключений (MAX_CONNECTIONS)
        2. Генерирует уникальный session_id
        3. Сохраняет соединение в active_connections и Redis
        4. Запускает асинхронную задачу для проверки активности соединения
        5. Обрабатывает входящие сообщения
        6. Очищает ресурсы при отключении
    """
    # Проверяем лимит подключений
    if len(active_connections) >= MAX_CONNECTIONS:
        await websocket.close(code=1008, reason="Достигнут лимит подключений")
        return

    await websocket.accept()
    
    # Генерируем UUID для сессии
    session_id = str(uuid.uuid4())
    # Сохраняем websocket локально и id в Redis
    active_connections[session_id] = websocket
    store_connection(session_id)

    # Отправляем ID сессии клиенту
    await websocket.send_json({
        "type": "connection_established",
        "session_id": session_id
    })
    
    # Создаем задачу для пинга соединения
    ping_task = create_task(ping_connection(websocket, session_id))
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Если это pong сообщение, пропускаем его обработку
            if data.get("type") == "pong":
                continue
                
            # Обработка остальных входящих WebSocket сообщений
            await websocket.send_text(f"Получено сообщение: {str(data)}")
            
    except WebSocketDisconnect:
        ping_task.cancel()  # Отменяем пинги при отключении
        del active_connections[session_id]
        remove_connection(session_id)
        
@app.post("/translation-result")
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
        await websocket.send_json(result.result)
        return {"status": "success", "message": "Результат отправлен клиенту"}
        
    except Exception as e:
        logger.error(f"Ошибка при отправке результата перевода: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
