import json
import regex
import signal
import asyncio
import logging
import aio_pika
import torch
import warnings
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from peft import PeftModel, PeftConfig
from jsonrpcserver import dispatch
from handlers.services_handler import translate
from transport.rabbitmq.MessageSender import MessageSender

from config import (
    RMQ_HOST as RABBIT_HOST,
    RMQ_PORT as RABBIT_PORT,
    RMQ_USERNAME as RABBIT_USER,
    RMQ_PASSWORD as RABBIT_PASSWORD,
    TRANSLATION_QUEUE as WORK_QUEUE,
    RESULT_QUEUE,
    ARDREYGPT_MODE,
    ARDREYGPT_MODEL_NAME,
    ARDREYGPT_MODEL_WEIGHTS
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class RequestHandler:
    """
    Обработчик запросов на перевод текста.
    
    Класс отвечает за:
    - Прослушивание очереди RabbitMQ для получения запросов на перевод
    - Обработку входящих сообщений и их валидацию
    - Отправку результатов перевода обратно через WebSocket
    - Корректное завершение работы при получении сигналов остановки
    
    Использует JSON-RPC для обработки запросов и aio-pika для работы с RabbitMQ.
    """
    
    def __init__(self):
        """
        Инициализация обработчика запросов.
        Устанавливает обработчики сигналов для корректного завершения работы.
        """
        self.connection = None
        self.channel = None
        self.should_stop = False
        
        # Инициализация модели перевода
        self.model = None
        self.tokenizer = None
        self.device = None
        if ARDREYGPT_MODE == "local":
            self._initialize_model()
            
        self._setup_signal_handlers()

    def _initialize_model(self):
        """Инициализация модели M2M100 с использованием кэширования"""
        try:
            # Отключаем предупреждения huggingface
            warnings.filterwarnings("ignore", 
                message=".*resume_download.*", 
                category=FutureWarning,
                module="huggingface_hub.*"
            )
            
            model_name = ARDREYGPT_MODEL_NAME
            logging.info(f"[RequestHandler] Initializing model {model_name}")
            
            # Пробуем загрузить модель из кэша
            try:
                self.tokenizer = M2M100Tokenizer.from_pretrained(
                    model_name,
                    local_files_only=True
                )
                self.model = M2M100ForConditionalGeneration.from_pretrained(
                    model_name,
                    local_files_only=True
                )
                logging.info("[RequestHandler] Model loaded from cache")
            except Exception as e:
                logging.info(f"[RequestHandler] Loading model from HuggingFace: {str(e)}")
                self.tokenizer = M2M100Tokenizer.from_pretrained(
                    model_name
                )
                self.model = M2M100ForConditionalGeneration.from_pretrained(
                    model_name
                )
            
            # Загружаем кастомные веса если указаны
            if ARDREYGPT_MODEL_WEIGHTS:
                try:
                    peft_config = PeftConfig.from_pretrained(ARDREYGPT_MODEL_WEIGHTS)

                    # Загружаем базовую модель
                    base_model = M2M100ForConditionalGeneration.from_pretrained(peft_config.base_model_name_or_path)

                    # Подключаем LoRA-адаптер
                    self.model = PeftModel.from_pretrained(base_model, ARDREYGPT_MODEL_WEIGHTS)

                    # Загружаем токенизатор (тот же, что и у базовой модели)
                    self.tokenizer = M2M100Tokenizer.from_pretrained(peft_config.base_model_name_or_path)
                    checkpoint = torch.load(ARDREYGPT_MODEL_WEIGHTS)
                    logging.info("[RequestHandler] Custom weights loaded successfully")

                except Exception as e:
                    logging.error(f"[RequestHandler] Error loading custom weights: {e}")
            
            # Перемещаем модель на доступное устройство
            device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
            self.device = torch.device(device)
            self.model.to(self.device)
            logging.info(f"[RequestHandler] Model initialized using device: {self.device}")
            
        except Exception as e:
            logging.error(f"[RequestHandler] Error initializing model: {e}")
            self.model = None
            self.tokenizer = None
            self.device = None

    def contains_letters_or_characters(self, text: str) -> bool:
        """Проверяет наличие букв или иероглифов в тексте"""
        # Проверяем наличие букв любого алфавита (включая кириллицу)
        # или иероглифов (CJK Unicode blocks)
        pattern = r'[\p{L}\p{Han}\p{Hiragana}\p{Katakana}]'
        return bool(regex.search(pattern, text))

    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    async def _send_error_message(self, connection_id: str, message: str):
        """Отправка сообщения об ошибке в очередь результатов"""
        error_message = {
            'connection_id': connection_id,
            'result': dict(),
            'error': message,
            'queue': RESULT_QUEUE
        }
        
        async with MessageSender() as sender:
            await sender.send_message(error_message)
    
    def _signal_handler(self, signum, frame):
        """
        Обработчик сигналов завершения работы.
        Обеспечивает корректное закрытие соединений при остановке сервиса.
        """
        message = f"Получен сигнал {signum}. Начинаем корректное завершение работы..."
        logging.info(message)
        
        # Создаем новый event loop для асинхронных вызовов в синхронном контексте
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
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
                payload = params.get('payload', {})
                
                service = params.get('queue', '')
                
                # Проверка наличия обязательных полей
                if not method_name or not connection_id or not payload:
                    error_msg = "[Обработчик] Отсутствуют обязательные поля: 'method', 'ws_session_id' или 'payload'"
                    logging.error(error_msg)
                    if not payload:
                        await self._send_error_message(
                            connection_id=connection_id or 'unknown',
                            message='Ошибка перевода! Не найден текст для перевода'
                        )
                    else:
                        await self._send_error_message(
                            connection_id=connection_id or 'unknown',
                            message='Ошибка перевода! Некорректный формат запроса'
                        )
                    return

                # Проверка содержимого текста
                text = payload.get('text', '')
                if not text:
                    await self._send_error_message(
                        connection_id=connection_id,
                        message='Ошибка перевода! Не найден текст для перевода'
                    )
                    return
                
                if not self.contains_letters_or_characters(text):
                    await self._send_error_message(
                        connection_id=connection_id,
                        message='Ошибка перевода! Текст должен содержать хотя бы одну букву или иероглиф'
                    )
                    return

                rpc = json.dumps({
                    "jsonrpc": "2.0",
                    "method": method_name,
                    "params": {
                        "payload": payload
                    },
                    "id": '1'
                })
                
                logging.info(f"[Обработчик] Отправка RPC запроса: {rpc}")
                response = dispatch(rpc, context=self)
                resp_str = str(response)

                if resp_str:
                    try:
                        resp = json.loads(resp_str)
                        if 'result' in resp:  
                            res_message = {
                                'connection_id': connection_id,
                                'result': resp['result'],
                                'queue': RESULT_QUEUE,
                                'error': ""
                            }
                            
                            if res_message['result'] and res_message['connection_id'] and service != 'telegram':
                                async with MessageSender() as sender:
                                    await sender.send_message(res_message)
                        else:
                            error_msg = f"[Обработчик] Ошибка от сервиса: {resp.get('error')}"
                            logging.error(error_msg)
                            
                            await self._send_error_message(
                                connection_id=connection_id,
                                message=resp.get('error').get('message', 'Ошибка перевода! Попробуйте повторить запрос позже')
                            )
                    except json.JSONDecodeError as e:
                        error_msg = f"[Обработчик] Ошибка разбора ответа: {e}"
                        logging.error(error_msg)
                        await self._send_error_message(
                            connection_id=connection_id,
                            message='Ошибка перевода! Попробуйте повторить запрос позже'
                        )
                else:
                    logging.info("[Обработчик] Уведомление (ответ не ожидается)")

        except Exception as e:
            error_msg = f"[Обработчик] Исключение: {e}"
            logging.exception(error_msg)
            try:
                connection_id = json.loads(message.body.decode()).get('ws_session_id', 'unknown')
                await self._send_error_message(
                    connection_id=connection_id,
                    message='Ошибка перевода! Попробуйте повторить запрос позже'
                )
            except:
                logging.exception("Не удалось отправить сообщение об ошибке")
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
                
                logging.info("[Консьюмер] Ожидание сообщений. Для выхода нажмите CTRL+C")
                
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        if self.should_stop:
                            break
                        await self._on_message(message)

            except aio_pika.exceptions.CONNECTION_EXCEPTIONS:
                if not self.should_stop:
                    error_msg = "[Консьюмер] Соединение потеряно, пытаемся переподключиться..."
                    logging.warning(error_msg)
                    await asyncio.sleep(5)
                    continue

            except Exception as e:
                error_msg = f"[Консьюмер] Неожиданная ошибка: {e}"
                logging.exception(error_msg)
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
                logging.info("[Консьюмер] Соединение закрыто")
            except Exception as e:
                error_msg = f"[Консьюмер] Ошибка при закрытии соединения: {e}"
                logging.error(error_msg)


async def main():
    handler = RequestHandler()
    await handler.start_consuming()

if __name__ == "__main__":
    asyncio.run(main())
