import aio_pika
import json
from typing import Optional, Dict, Any

from transport.rabbitmq.Message import Message
from config import RMQ_USERNAME, RMQ_PASSWORD


class MessageSender:
    def __init__(self, host: str = "localhost", port: int = 15672):
        self.host = host
        self.port = port
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.translation_queue: Optional[aio_pika.Queue] = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(
            f"amqp://{RMQ_USERNAME}:{RMQ_PASSWORD}@{self.host}:{self.port}/"
        )
        self.channel = await self.connection.channel()
        
        # Создаем очередь для запросов на перевод
        self.translation_queue = await self.channel.declare_queue(
            "translation_requests",
            durable=True
        )

    async def send_translation_request(self, text: str, translator_type: str, ws_session_id: str):
        if not self.connection or self.connection.is_closed:
            await self.connect()

        message = {
            "text": text,
            "type": translator_type,
            "ws_session_id": ws_session_id
        }

        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key="translation_requests"
        )

    async def send_result(self, ws_session_id: str, result: Dict[str, Any]):
        if not self.connection or self.connection.is_closed:
            await self.connect()

        message = {
            "ws_session_id": ws_session_id,
            "result": result
        }

        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key="translation_results"
        )

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

    def send(self, message: Message):
        queue = message.get_queue()
        self.channel.queue_declare(queue=queue)  # Создание очереди (если не существует)

        data = message.get_data()

        self.channel.basic_publish(
            exchange='',
            routing_key=queue,
            body=data
        )

        print(f"Sent: '{data}'")

        # Закрытие соединения
        self.connection.close()
