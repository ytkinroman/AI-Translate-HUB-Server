import json
import logging
import signal
import time
import pika
from fastapi import WebSocket

from config import (
    RABBIT_HOST,
    RABBIT_PORT,
    RABBIT_USER,
    RABBIT_PASSWORD,
)
from transport.redis.redis_client import check_connection

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Название очереди результатов
RESULT_QUEUE = 'results'

class ResultHandler:
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

    def _signal_handler(self, signum, frame):
        """Обработчик сигналов"""
        message = f"Received signal {signum}. Starting graceful shutdown..."
        logging.info(message)
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
                self.channel.queue_declare(queue=RESULT_QUEUE, durable=True)
                self.channel.basic_qos(prefetch_count=1)
                logging.info("Successfully connected to RabbitMQ")
                return True
            except Exception as e:
                if self.should_stop:
                    break
                error_msg = f"Failed to connect to RabbitMQ: {e}"
                logging.error(error_msg)
                time.sleep(5)
        return False

    def _on_message(self, ch, method, properties, body):
        """Обработка входящего сообщения с результатом"""
        try:
            logging.info(f"[Handler] Received result message: {body}")
            message = json.loads(body)
            connection_id = message.get('connection_id')
            result = message.get('result')
            
            if not connection_id or result is None:
                error_msg = "[Handler] Missing 'connection_id' or 'result'"
                logging.error(error_msg)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Проверяем существование соединения в Redis
            if check_connection(connection_id):
                try:
                    # В этом месте websocket должен быть получен из активных соединений app.py
                    # Но так как сервисы независимы, это невозможно
                    # Поэтому мы просто подтверждаем получение сообщения
                    logging.info(f"[Handler] Connection {connection_id} exists in Redis")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as ws_error:
                    logging.error(f"[Handler] Failed to process result: {ws_error}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            else:
                logging.warning(f"[Handler] Connection {connection_id} not found in Redis")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                
        except json.JSONDecodeError as e:
            error_msg = f"[Handler] Invalid JSON in message: {e}"
            logging.error(error_msg)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            error_msg = f"[Handler] Error processing result: {e}"
            logging.error(error_msg)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        """Запуск прослушивания очереди результатов"""
        while not self.should_stop:
            try:
                if not self.connection or self.connection.is_closed:
                    if not self._setup_connection():
                        continue

                self.channel.basic_consume(
                    queue=RESULT_QUEUE,
                    on_message_callback=self._on_message
                )
                logging.info("[Consumer] Waiting for results. To exit press CTRL+C")
                self.channel.start_consuming()

            except pika.exceptions.ConnectionClosedByBroker:
                if not self.should_stop:
                    logging.warning("[Consumer] Connection was closed by broker, retrying...")
                    continue

            except pika.exceptions.AMQPChannelError as e:
                logging.error(f"[Consumer] Channel error: {e}, stopping...")
                break

            except pika.exceptions.AMQPConnectionError:
                if not self.should_stop:
                    logging.warning("[Consumer] Connection was lost, retrying...")
                    continue

            except Exception as e:
                logging.exception(f"[Consumer] Unexpected error: {e}")
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
                logging.error(f"[Consumer] Error closing connection: {e}")
