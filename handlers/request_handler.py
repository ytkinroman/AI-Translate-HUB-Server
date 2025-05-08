import json
import logging
import signal
import time
from typing import Dict, Any

import aio_pika
from jsonrpcserver import dispatch
from handlers.services_handler import translate
from transport.rabbitmq.MessageSender import MessageSender
import asyncio
from config import (
    RMQ_HOST as RABBIT_HOST,
    RMQ_PORT as RABBIT_PORT,
    RMQ_USERNAME as RABBIT_USER,
    RMQ_PASSWORD as RABBIT_PASSWORD,
    TRANSLATION_QUEUE as WORK_QUEUE,
    RESULT_QUEUE
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class RequestHandler:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.should_stop = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    # async def _send_error_notification(self, error_message: str):
    #     """Отправка уведомления об ошибке через очередь requests"""
    #     message = {
    #         'service': 'telegram',
    #         'chat_id': None,  # Будет использоваться DEBUG_RECIPIENTS из конфига
    #         'payload': error_message,
    #         'message_id': str(time.time())  # Используем время как уникальный ID
    #     }
    #     try:
    #         async with MessageSender() as sender:
    #             await sender.send_message(message)
    #     except Exception as e:
    #         logging.error(f"Failed to send error notification: {e}")

    def _signal_handler(self, signum, frame):
        """Обработчик сигналов"""
        message = f"Received signal {signum}. Starting graceful shutdown..."
        logging.info(message)
        
        # Создаем новый event loop для асинхронных вызовов в синхронном контексте
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаем асинхронное уведомление об ошибке
        #loop.run_until_complete(self._send_error_notification(message))
        
        self.should_stop = True
        if self.connection and not self.connection.is_closed:
            loop.run_until_complete(self.connection.close())
        
        loop.close()

    async def _on_message(self, message: aio_pika.IncomingMessage):
        """Обработка входящего сообщения"""
        try:
            async with message.process():
                logging.info(f"[Handler] Received message: {message.body}")
                params = json.loads(message.body.decode())
                method_name = params.get('method')
                connection_id = params.get('ws_session_id')
                payload = params.get('payload', {})  # Создаем копию, чтобы не изменять оригинал
                
                # Переименовываем translator_type в translator_code если есть
                if 'translator_type' in payload:
                    payload['translator_code'] = payload.pop('translator_type')
                service = params.get('queue', '')
                
                if not method_name or not connection_id or not payload:
                    error_msg = "[Handler] Missing required fields: 'method', 'ws_session_id' or 'payload'"
                    logging.error(error_msg)
                    #await self._send_error_notification(error_msg)
                    return

                rpc = json.dumps({
                    "jsonrpc": "2.0",
                    "method": method_name,
                    "params": {
                        "payload": payload
                    },
                    "id": '1'
                })
                
                logging.info(f"[Handler] Dispatching RPC: {rpc}")
                response = dispatch(rpc, context=self)
                resp_str = str(response)

                if resp_str:
                    try:
                        resp = json.loads(resp_str)
                        if 'result' in resp:  
                            res_message = {
                                'connection_id': connection_id,
                                'result': resp['result'],
                                'queue': RESULT_QUEUE
                            }
                            
                            if res_message['result'] and res_message['connection_id'] and service != 'telegram':
                                async with MessageSender() as sender:
                                    await sender.send_message(res_message)
                        else:
                            error_msg = f"[Handler] Error from service: {resp.get('error')}"
                            logging.error(error_msg)
                            #await self._send_error_notification(error_msg)
                    except json.JSONDecodeError as e:
                        error_msg = f"[Handler] Error parsing response: {e}"
                        logging.error(error_msg)
                        #await self._send_error_notification(error_msg)
                else:
                    logging.info("[Handler] Notification (no response expected)")

        except Exception as e:
            error_msg = f"[Handler] Exception: {e}"
            logging.exception(error_msg)
            #await self._send_error_notification(error_msg)
            await message.reject(requeue=False)

    async def start_consuming(self):
        """Запуск прослушивания очереди"""
        while not self.should_stop:
            try:
                # Устанавливаем соединение
                self.connection = await aio_pika.connect_robust(
                    f"amqp://{RABBIT_USER}:{RABBIT_PASSWORD}@{RABBIT_HOST}:{RABBIT_PORT}/"
                )
                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=1)

                # Объявляем очередь
                queue = await self.channel.declare_queue(WORK_QUEUE, durable=True)
                
                logging.info("[Consumer] Waiting for messages. To exit press CTRL+C")
                
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        if self.should_stop:
                            break
                        await self._on_message(message)

            except aio_pika.exceptions.CONNECTION_EXCEPTIONS:
                if not self.should_stop:
                    error_msg = "[Consumer] Connection was lost, retrying..."
                    logging.warning(error_msg)
                    #await self._send_error_notification(error_msg)
                    await asyncio.sleep(5)
                    continue

            except Exception as e:
                error_msg = f"[Consumer] Unexpected error: {e}"
                logging.exception(error_msg)
                #await self._send_error_notification(error_msg)
                if not self.should_stop:
                    await asyncio.sleep(5)
                    continue
                break

            if self.should_stop:
                break

        # Graceful shutdown
        if self.connection and not self.connection.is_closed:
            try:
                await self.connection.close()
                logging.info("[Consumer] Connection closed")
            except Exception as e:
                error_msg = f"[Consumer] Error closing connection: {e}"
                logging.error(error_msg)
                #await self._send_error_notification(error_msg)


async def main():
    handler = RequestHandler()
    await handler.start_consuming()

if __name__ == "__main__":
    asyncio.run(main())
