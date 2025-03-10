import pika

from transport.rabbitmq.Message import Message
from config import RMQ_USERNAME, RMQ_PASSWORD


class MessageSender:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        # Параметры подключения
        connection_params = pika.ConnectionParameters(
            host='localhost',
            port=15672,
            virtual_host='/',
            credentials=pika.PlainCredentials(
                username=RMQ_USERNAME,
                password=RMQ_PASSWORD
            )
        )

        # Установка соединения
        self.connection = pika.BlockingConnection(connection_params)

        # Создание канала
        self.channel = self.connection.channel()

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
