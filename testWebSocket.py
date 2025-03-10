from fastapi import FastAPI, WebSocket, Query
from starlette.responses import JSONResponse
# from typing import Annotated
import json
import uuid
# import pika
import asyncio

# from config import RMQ_USERNAME, RMQ_PASSWORD, RMQ_QUEUE_4_ANSWERS, RMQ_QUEUE_4_TRANSLATE
# from modules.handlers.TranslateHandler import TranslateHandler
# from transport.rabbitmq.MessageSender import MessageSender
# from modules.handlers.AnswerHandler import AnswerHandler
# from transport.rabbitmq.Message import Message


# def connect():
#     # Параметры подключения
#     connection_params = pika.ConnectionParameters(
#         host='localhost',
#         port=5672,
#         virtual_host='/',
#         credentials=pika.PlainCredentials(
#             username=RMQ_USERNAME,
#             password=RMQ_PASSWORD
#         )
#     )
#
#     # Установка соединения
#     connection = pika.BlockingConnection(connection_params)
#
#     # Создание канала
#     return connection.channel()
#
#
# async def subscribe(ch, queue_name, callback):
#     # Подписка на очередь и установка обработчика сообщений
#     ch.basic_consume(
#         queue=queue_name,
#         on_message_callback=callback,
#         auto_ack=True  # Автоматическое подтверждение обработки сообщений
#     )
#
#     print('Waiting for messages')
#     await ch.start_consuming()
#

app = FastAPI()

# Словарь для хранения активных WebSocket-соединений: connection_id -> WebSocket
active_connections: dict[str, WebSocket] = {}
# channel = connect()
# subscribe(channel, RMQ_QUEUE_4_ANSWERS, AnswerHandler)
# subscribe(channel, RMQ_QUEUE_4_TRANSLATE, TranslateHandler)


@app.get("/")
async def get():
    return JSONResponse(content={"message": "Welcome to translate server!"})


@app.get("/api/v1/translate")
async def get(text, lang):
    if text & lang:
        print(lang)
    return JSONResponse(content={"message": "Welcome to translate server!"})


# Функция для отправки сообщения пользователю, если он подключен
async def send_to_user(user_id: int, message: dict):
    """Отправить сообщение пользователю, если он подключен."""
    if user_id in active_connections:
        websocket = active_connections[user_id]
        # Отправляем сообщение в формате JSON
        await websocket.send_json(message)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Генерация уникального идентификатора для соединения
    connection_id = str(uuid.uuid4())
    active_connections[connection_id] = websocket
    # Отправка идентификатора клиенту
    await websocket.send_text(json.dumps({"connection_id": connection_id}))

    try:
        while True:
            # # Получаем сообщение от клиента
            message = await websocket.receive_text()
            # print(f"Сообщение от {connection_id}: {message}")
            #
            # # Отправляем результат обратно клиенту
            await websocket.send_json({"your_message": message})
            with open('testWebSocket.txt', 'w+') as file:
                file.write(message)
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Соединение {connection_id} закрыто: {e}")
    finally:
        active_connections.pop(connection_id, None)
