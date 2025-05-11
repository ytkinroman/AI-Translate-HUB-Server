import json
import logging
import signal
import time
import aiohttp
import asyncio
import pika

from config import (
    RMQ_HOST as RABBIT_HOST,
    RMQ_PORT as RABBIT_PORT,
    RMQ_USERNAME as RABBIT_USER,
    RMQ_PASSWORD as RABBIT_PASSWORD,
    RESULT_QUEUE,
    APP_HOST,
    APP_PORT
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class ResultHandler:
    """
    Обработчик результатов перевода.
    
    Класс отвечает за:
    - Получение результатов перевода из очереди RabbitMQ
    - Отправку результатов клиентам через HTTP
    - Подтверждение обработки сообщений
    - Корректное завершение работы при получении сигналов остановки
    
    Использует блокирующее подключение к RabbitMQ и асинхронные HTTP запросы
    для отправки результатов.
    """
    
    def __init__(self):
        """
        Инициализация обработчика результатов.
        Устанавливает обработчики сигналов и создает подключение к RabbitMQ.
        """
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
        message = f"Получен сигнал {signum}. Начинаем корректное завершение работы..."
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
                logging.info("[Обработчик результата] Успешно подключено к RabbitMQ")
                return True
            except Exception as e:
                if self.should_stop:
                    break
                error_msg = f"[Обработчик результата] Не удалось подключиться к RabbitMQ: {e}"
                logging.error(error_msg)
                time.sleep(5)
        return False

    def _on_message(self, ch, method, properties, body):
        """Обработка входящего сообщения с результатом"""
        try:
            logging.info(f"[Обработчик результата] Получено сообщение: {body}")
            message = json.loads(body.decode('utf-8'))
            connection_id = message.get('connection_id')
            result = message.get('result')
            error = message.get('error')
            
            if not connection_id or (result is None and error is None):
                error_msg = "[Обработчик результата] Отсутствует 'connection_id' или оба поля 'result' и 'error' пустые"
                logging.error(error_msg)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Отправляем результат через HTTP
            try:
                # Создаем новый event loop для асинхронного HTTP запроса
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def send_result():
                    async with aiohttp.ClientSession() as session:
                        url = f"http://{APP_HOST}:{APP_PORT}/translation-result"
                        # Формируем payload с правильной структурой для всех случаев
                        payload = {
                            "connection_id": connection_id,
                            "result": result if result else {"result": {"success": False, "text": "", "source_language": ""}},
                            "error": error
                        }
                        logging.info(f"[Обработчик результата] Подготовленные данные для отправки: {payload}")
                        async with session.post(url, json=payload) as response:
                            if response.status == 200:
                                logging.info(f"[Обработчик результата] Успешно отправлен результат для соединения {connection_id}")
                                return True
                            else:
                                error_text = await response.text()
                                logging.error(f"[Обработчик результата] Не удалось отправить результат. Статус: {response.status}, Ошибка: {error_text}")
                                return False
                
                success = loop.run_until_complete(send_result())
                if success:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    
            except Exception as e:
                logging.error(f"[Обработчик результата] Не удалось отправить результат: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            finally:
                loop.close()
                
        except json.JSONDecodeError as e:
            error_msg = f"[Обработчик результата] Некорректный JSON в сообщении: {e}"
            logging.error(error_msg)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            error_msg = f"[Обработчик результата] Ошибка обработки результата: {e}"
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
                logging.info("[Обработчик результата] Ожидание результатов. Для выхода нажмите CTRL+C")
                self.channel.start_consuming()

            except pika.exceptions.ConnectionClosedByBroker:
                if not self.should_stop:
                    logging.warning("[Обработчик результата] Соединение закрыто брокером, пытаемся переподключиться...")
                    continue

            except pika.exceptions.AMQPChannelError as e:
                logging.error(f"[Обработчик результата] Ошибка канала: {e}, останавливаемся...")
                break

            except pika.exceptions.AMQPConnectionError:
                if not self.should_stop:
                    logging.warning("[Обработчик результата] Соединение потеряно, пытаемся переподключиться...")
                    continue

            except Exception as e:
                logging.exception(f"[Обработчик результата] Неожиданная ошибка: {e}")
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
                logging.info("[Обработчик результата] Соединение закрыто")
            except Exception as e:
                logging.error(f"[Обработчик результата] Ошибка при закрытии соединения: {e}")

if __name__ == "__main__":
    handler = ResultHandler()
    handler.start_consuming()
