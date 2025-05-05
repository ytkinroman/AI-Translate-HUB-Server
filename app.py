import uuid
import time
import logging
from typing import Dict
from pydantic import BaseModel
from asyncio import create_task, sleep
from fastapi.middleware.cors import CORSMiddleware
from transport.rabbitmq.MessageSender import MessageSender
from transport.redis.redis_client import store_connection, remove_connection, check_connection
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from config import (
    LOG_LEVEL, 
    LOG_FORMAT,
    CORS_ORIGINS,
    WS_PING_TIMEOUT,
    MAX_CONNECTIONS,
    WS_PING_INTERVAL,
)

# Хранение активных WebSocket соединений локально
active_connections: Dict[str, WebSocket] = {}

# Настройка логирования
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

message_sender = MessageSender()

class TranslationRequest(BaseModel):
    text: str
    translator_type: str
    ws_session_id: str

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
    try:        
        # Проверяем, существует ли сессия
        if not check_connection(request.ws_session_id):
            return {"status": "error", "message": "Invalid session ID"}
            
        # Отправляем запрос через MessageSender
        await message_sender.send_translation_request(
            text=request.text,
            translator_type=request.translator_type,
            ws_session_id=request.ws_session_id
        )
        return {"status": "success", "message": "Translation request accepted"}
    except Exception as e:
        logger.error(f"Error in translate_text: {str(e)}")
        return {"status": "error", "message": str(e)}


async def ping_connection(websocket: WebSocket, session_id: str):
    """
    Асинхронная функция для периодической проверки активности WebSocket соединения.
    
    Args:
        websocket (WebSocket): Активное WebSocket соединение для проверки
        session_id (str): Уникальный идентификатор сессии для логирования

    Механизм работы:
        - Отправляет ping-сообщение каждые WS_PING_INTERVAL секунд
        - Если ответ не получен в течение WS_PING_TIMEOUT секунд, соединение закрывается
        - Логирует все ошибки и таймауты для отладки
    """
    while True:
        try:
            await sleep(WS_PING_INTERVAL)
            ping_start = time.time()
            await websocket.ping()
            
            # Если превысили таймаут
            if time.time() - ping_start > WS_PING_TIMEOUT:
                logger.warning(f"WebSocket ping timeout for session {session_id}")
                await websocket.close(code=1001)  # Going away
                break
                
        except Exception as e:
            logger.error(f"Error in ping for session {session_id}: {str(e)}")
            break

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint для установки и поддержания WebSocket соединения.
    
    Args:
        websocket (WebSocket): Входящее WebSocket соединение

    Функциональность:
        1. Проверяет лимит подключений (MAX_CONNECTIONS)
        2. Генерирует уникальный session_id
        3. Сохраняет соединение в active_connections и connections.csv
        4. Запускает асинхронную задачу для проверки активности соединения:
           - Пинги каждые WS_PING_INTERVAL секунд
           - Таймаут WS_PING_TIMEOUT секунд
        5. Обрабатывает входящие сообщения
        6. При отключении:
           - Отменяет задачу пингов
           - Удаляет соединение из active_connections
           - Обновляет connections.csv
    """
    # Проверяем лимит подключений
    if len(active_connections) >= MAX_CONNECTIONS:
        await websocket.close(code=1008, reason="Maximum connections reached")
        return

    await websocket.accept()
    
    # Генерируем UUID для сессии
    session_id = str(uuid.uuid4())
    # Сохраняем websocket локально и id в Redis
    active_connections[session_id] = websocket
    store_connection(session_id, websocket)

    # Отправляем ID сессии клиенту
    await websocket.send_json({
        "type": "connection_established",
        "session_id": session_id
    })
    
    # Создаем задачу для пинга соединения
    ping_task = create_task(ping_connection(websocket, session_id))
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Обработка входящих WebSocket сообщений
            await websocket.send_text(f"Message received: {data}")
            
    except WebSocketDisconnect:
        ping_task.cancel()  # Отменяем пинги при отключении
        del active_connections[session_id]
        
        remove_connection(session_id)
