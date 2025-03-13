from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from typing import Dict, List
from transport.rabbitmq.MessageHandler import MessageHandler
from transport.rabbitmq.MessageSender import MessageSender
import uuid

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранение активных WebSocket соединений
active_connections: Dict[str, WebSocket] = {}

# Инициализация обработчиков
message_handler = MessageHandler()
message_sender = MessageSender()


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
        return {"status": "error", "message": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Генерируем UUID для сессии
    session_id = str(uuid.uuid4())
    active_connections[session_id] = websocket
    
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


@app.on_event("startup")
async def startup_event():
    # Запуск обработчика сообщений
    await message_handler.start()
    # Устанавливаем callback для отправки результатов через WebSocket
    message_handler.set_result_callback(send_result_to_client)
