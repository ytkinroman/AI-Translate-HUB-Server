from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import csv
from typing import Dict, List
from transport.rabbitmq.MessageHandler import MessageHandler
from transport.rabbitmq.MessageSender import MessageSender
import uuid
import asyncio
import os
import logging
from config import (
    LOG_LEVEL, LOG_FORMAT,
    CORS_ORIGINS,
    MAX_CONNECTIONS,
    WS_PING_INTERVAL,
    WS_PING_TIMEOUT
)

# Настройка логирования
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранение активных WebSocket соединений
active_connections: Dict[str, WebSocket] = {}

# Инициализация обработчиков
message_handlers: List[MessageHandler] = []
message_sender = MessageSender()

# Количество воркеров (можно настроить через переменную окружения)
NUM_WORKERS = int(os.getenv("NUM_WORKERS", "3"))


class TranslationRequest(BaseModel):
    text: str
    translator_type: str
    ws_session_id: str


@app.post("/translate")
async def translate_text(request: TranslationRequest):
    try:
        # Проверяем, существует ли сессия
        if request.ws_session_id not in active_connections:
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if len(active_connections) >= MAX_CONNECTIONS:
        await websocket.close(code=1008, reason="Maximum connections reached")
        return

    await websocket.accept()
    
    # Генерируем UUID для сессии
    session_id = str(uuid.uuid4())
    active_connections[session_id] = websocket
    with open("classmates.csv", encoding='utf-8') as w_file:
        file_writer = csv.writer(w_file)
        file_writer.writerow([session_id, websocket])

    # Отправляем ID сессии клиенту
    await websocket.send_json({
        "type": "connection_established",
        "session_id": session_id
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            # Обработка входящих WebSocket сообщений
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        del active_connections[session_id]


async def send_result_to_client(data: dict):
    ws_session_id = data.get("ws_session_id")
    if ws_session_id in active_connections:
        websocket = active_connections[ws_session_id]
        await websocket.send_json(data)


async def start_worker(worker_id: int):
    try:
        handler = MessageHandler(worker_id=worker_id)
        await handler.start()
        message_handlers.append(handler)
        handler.set_result_callback(send_result_to_client)
        logger.info(f"Worker {worker_id} started successfully")
    except Exception as e:
        logger.error(f"Error starting worker {worker_id}: {str(e)}")


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {NUM_WORKERS} RabbitMQ workers")
    # Запуск нескольких воркеров
    for i in range(NUM_WORKERS):
        asyncio.create_task(start_worker(i))


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down RabbitMQ workers")
    # Закрытие всех воркеров
    for handler in message_handlers:
        try:
            await handler.close()
        except Exception as e:
            logger.error(f"Error closing worker: {str(e)}")
