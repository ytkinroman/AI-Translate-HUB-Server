from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import csv
import time
from typing import Dict, List
from asyncio import create_task, sleep
from transport.rabbitmq.MessageHandler import MessageHandler
from transport.rabbitmq.MessageSender import MessageSender
import uuid

import logging

from config import (
    LOG_LEVEL, LOG_FORMAT,
    CORS_ORIGINS,
    MAX_CONNECTIONS,
    WS_PING_INTERVAL,
    WS_PING_TIMEOUT
)

# Временное хранение активных WebSocket соединений
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
        with open("connections.csv", encoding='utf-8') as w_file:
            # Читаем все активные соединения
            file_reader = csv.reader(w_file)
            active_connections = dict(file_reader)
        
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


async def ping_connection(websocket: WebSocket, session_id: str):
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
    with open("connections.csv", encoding='utf-8') as w_file:
            # Читаем все активные соединения
            file_reader = csv.reader(w_file)
            active_connections = dict(file_reader)
    
    if len(active_connections) >= MAX_CONNECTIONS:
        await websocket.close(code=1008, reason="Maximum connections reached")
        return

    await websocket.accept()
    
    # Генерируем UUID для сессии
    session_id = str(uuid.uuid4())
    active_connections[session_id] = websocket
    with open("connections.csv", encoding='utf-8') as w_file:
        file_writer = csv.writer(w_file)
        file_writer.writerow([session_id, websocket])

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
        
        with open("connections.csv", encoding='utf-8') as w_file:
            file_reader = csv.reader(w_file)
            rows = list(file_reader)
            
            # Удаляем строку с отключенной сессией
            rows = [row for row in rows if row[0] != session_id]
            
            # Записываем обновленный список соединений
            file_writer = csv.writer(w_file)
            file_writer.writerows(rows)
