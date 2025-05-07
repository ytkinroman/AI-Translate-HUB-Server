import json
import logging
import signal
import time
from typing import Dict, Any

import pika
from jsonrpcserver import dispatch

from transport.rabbitmq.MessageSender import MessageSender
from config import (
    RMQ_HOST as RABBIT_HOST,
    RMQ_PORT as RABBIT_PORT,
    RMQ_USERNAME as RABBIT_USER,
    RMQ_PASSWORD as RABBIT_PASSWORD,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Название очередей
WORK_QUEUE = 'requests'
RESULT_QUEUE = 'results'

class RequestHandler:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.should_stop = False
        self._setup_signal_handlers()
        self._setup_connection()

    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _send_error_notification(self, error_message: str):
        """Отправка уведомления об ошибке через очередь requests"""
        message = {
            'service': 'telegram',
            'chat_id': None,  # Будет использоваться DEBUG_RECIPIENTS из конфига
            'payload': error_message,
            'message_id': str(time.time())  # Используем время как уникальный ID
        }
        try:
            with MessageSender() as sender:
                sender.send_message(WORK_QUEUE, message)
        except Exception as e:
            logging.error(f"Failed to send error notification: {e}")

    def _signal_handler(self, signum, frame):
        """Обработчик сигналов"""
        message = f"Received signal {signum}. Starting graceful shutdown..."
        logging.info(message)
        self._send_error_notification(message)
        self.should_stop = True
        if self.connection and not self.connection.is_closed:
            self.connection.close()

    def _setup_connection(self):
        """Установка соединения с RabbitMQ"""
        while not self.should_stop:
            try:
                params = pika.ConnectionParameters(
                    host=RABBIT_HOST,
                    port=RABBIT_PORT,
                    credentials=pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD),
                    heartbeat=30,
                    socket_timeout=300,
                    connection_attempts=3,
                    retry_delay=5
                )
                self.connection = pika.BlockingConnection(params)
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=WORK_QUEUE, durable=True)
                self.channel.basic_qos(prefetch_count=1)
                logging.info("Successfully connected to RabbitMQ")
                return True
            except Exception as e:
                if self.should_stop:
                    break
                error_msg = f"Failed to connect to RabbitMQ: {e}"
                logging.error(error_msg)
                self._send_error_notification(error_msg)
                time.sleep(5)
        return False

    def _on_message(self, ch, method, properties, body):
        """Обработка входящего сообщения"""
        try:
            logging.info(f"[Handler] Received message: {body}")
            params = json.loads(body)
            service = params.get('service')
            connection_id = params.get('connection_id')
            
            if not service or not connection_id:
                error_msg = "[Handler] Missing 'service' or 'connection_id'"
                logging.error(error_msg)
                self._send_error_notification(error_msg)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            rpc = json.dumps({
                "jsonrpc": "2.0",
                "method": service,
                "params": [params.get('payload')],
                "id": params.get('message_id', '1')
            })
            
            logging.info(f"[Handler] Dispatching RPC: {rpc}")
            response = dispatch(rpc)
            resp_str = str(response)

            if resp_str:
                resp = json.loads(resp_str)
                if 'result' in resp:  
                    message = {
                        'connection_id': connection_id,
                        'result': resp['result']
                    }
                    
                    logging.info(f"[Handler] Message: {message['result']}")
                    if message['result'] and message['connection_id'] and service != 'telegram':
                        with MessageSender() as sender:
                            sender.send_message(RESULT_QUEUE, json.dumps(message))
                else:
                    error_msg = f"[Handler] Error from service: {resp.get('error')}"
                    logging.error(error_msg)
                    self._send_error_notification(error_msg)
            else:
                logging.info("[Handler] Notification (no response expected)")

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            error_msg = f"[Handler] Exception: {e}"
            logging.exception(error_msg)
            self._send_error_notification(error_msg)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        """Запуск прослушивания очереди"""
        while not self.should_stop:
            try:
                if not self.connection or self.connection.is_closed:
                    if not self._setup_connection():
                        continue

                self.channel.basic_consume(
                    queue=WORK_QUEUE,
                    on_message_callback=self._on_message
                )
                logging.info("[Consumer] Waiting for messages. To exit press CTRL+C")
                self.channel.start_consuming()

            except pika.exceptions.ConnectionClosedByBroker:
                if not self.should_stop:
                    error_msg = "[Consumer] Connection was closed by broker, retrying..."
                    logging.warning(error_msg)
                    self._send_error_notification(error_msg)
                    continue

            except pika.exceptions.AMQPChannelError as e:
                error_msg = f"[Consumer] Channel error: {e}, stopping..."
                logging.error(error_msg)
                self._send_error_notification(error_msg)
                break

            except pika.exceptions.AMQPConnectionError:
                if not self.should_stop:
                    error_msg = "[Consumer] Connection was lost, retrying..."
                    logging.warning(error_msg)
                    self._send_error_notification(error_msg)
                    continue

            except Exception as e:
                error_msg = f"[Consumer] Unexpected error: {e}"
                logging.exception(error_msg)
                self._send_error_notification(error_msg)
                if not self.should_stop:
                    time.sleep(5)
                    continue
                break

            if self.should_stop:
                break

        # Graceful shutdown
        if self.connection and not self.connection.is_closed:
            try:
                self.connection.close()
                logging.info("[Consumer] Connection closed")
            except Exception as e:
                error_msg = f"[Consumer] Error closing connection: {e}"
                logging.error(error_msg)
                self._send_error_notification(error_msg)


if __name__ == "__main__":
    handler = RequestHandler()
    handler.start_consuming()
