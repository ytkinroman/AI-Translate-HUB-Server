import aio_pika
import json
from typing import Optional, Callable, Dict, Any
from modules.translators.translator_handler import TranslatorHandler
from transport.rabbitmq.MessageSender import MessageSender

class MessageHandler:
    def __init__(self, host: str = "localhost", port: int = 5672):
        self.host = host
        self.port = port
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.translation_queue: Optional[aio_pika.Queue] = None
        self.result_queue: Optional[aio_pika.Queue] = None
        self.translator_handler = TranslatorHandler()
        self.message_sender = MessageSender(host, port)
        self.result_callback: Optional[Callable] = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(
            f"amqp://guest:guest@{self.host}:{self.port}/"
        )
        self.channel = await self.connection.channel()
        
        # Создаем очереди
        self.translation_queue = await self.channel.declare_queue(
            "translation_requests",
            durable=True
        )
        self.result_queue = await self.channel.declare_queue(
            "translation_results",
            durable=True
        )

    async def start(self):
        await self.connect()
        await self.consume_translation_requests()
        await self.consume_results()

    async def consume_translation_requests(self):
        async def process_message(message):
            async with message.process():
                data = json.loads(message.body.decode())
                result = self.translator_handler.handle_translation(data)
                
                # Отправляем результат через MessageSender
                await self.message_sender.send_result(
                    ws_session_id=data["ws_session_id"],
                    result=result
                )

        await self.translation_queue.consume(process_message)

    async def consume_results(self):
        async def process_message(message):
            async with message.process():
                data = json.loads(message.body.decode())
                if self.result_callback:
                    await self.result_callback(data)

        await self.result_queue.consume(process_message)

    def set_result_callback(self, callback: Callable):
        self.result_callback = callback

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        await self.message_sender.close()

