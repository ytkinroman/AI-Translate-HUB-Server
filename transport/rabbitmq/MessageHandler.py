import aio_pika
import json
from typing import Optional, Callable, Dict, Any
from modules.handlers.translator_handler import TranslatorHandler
from transport.rabbitmq.MessageSender import MessageSender
from config import RMQ_USERNAME, RMQ_PASSWORD
import logging

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self, worker_id: int, host: str = "localhost", port: int = 15672):
        self.worker_id = worker_id
        self.host = host
        self.port = port
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.translation_queue: Optional[aio_pika.Queue] = None
        self.result_queue: Optional[aio_pika.Queue] = None
        self.translator_handler = TranslatorHandler()
        self.message_sender = MessageSender(host, port)
        self.result_callback: Optional[Callable] = None
        self._running = False

    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(
                f"amqp://{RMQ_USERNAME}:{RMQ_PASSWORD}@{self.host}:{self.port}/"
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

            # Устанавливаем prefetch_count=1 для fair dispatch
            await self.channel.set_qos(prefetch_count=1)
            logger.info(f"Worker {self.worker_id} connected to RabbitMQ successfully")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed to connect to RabbitMQ: {str(e)}")
            raise

    async def start(self):
        if self._running:
            logger.warning(f"Worker {self.worker_id} is already running")
            return

        try:
            await self.connect()
            self._running = True
            await self.consume_translation_requests()
            await self.consume_results()
        except Exception as e:
            self._running = False
            logger.error(f"Worker {self.worker_id} failed to start: {str(e)}")
            raise

    async def consume_translation_requests(self):
        async def process_message(message):
            if not self._running:
                return

            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    logger.info(f"Worker {self.worker_id} processing message: {data}")
                    
                    result = self.translator_handler.handle_translation(data)
                    
                    # Отправляем результат через MessageSender
                    await self.message_sender.send_result(
                        ws_session_id=data["ws_session_id"],
                        result=result
                    )
                    logger.info(f"Worker {self.worker_id} successfully processed message")
                except Exception as e:
                    logger.error(f"Worker {self.worker_id} error processing message: {str(e)}")
                    # В случае ошибки отправляем сообщение об ошибке
                    await self.message_sender.send_result(
                        ws_session_id=data.get("ws_session_id", "unknown"),
                        result={"error": str(e)}
                    )

        try:
            await self.translation_queue.consume(process_message)
            logger.info(f"Worker {self.worker_id} started consuming translation requests")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed to start consuming: {str(e)}")
            raise

    async def consume_results(self):
        async def process_message(message):
            if not self._running:
                return

            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    if self.result_callback:
                        await self.result_callback(data)
                except Exception as e:
                    logger.error(f"Worker {self.worker_id} error processing result: {str(e)}")

        try:
            await self.result_queue.consume(process_message)
            logger.info(f"Worker {self.worker_id} started consuming results")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed to start consuming results: {str(e)}")
            raise

    def set_result_callback(self, callback: Callable):
        self.result_callback = callback

    async def close(self):
        self._running = False
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            await self.message_sender.close()
            logger.info(f"Worker {self.worker_id} closed successfully")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error during closing: {str(e)}")
            raise

