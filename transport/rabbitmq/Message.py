class Message:
    """
    Класс, представляющий сообщение для отправки через RabbitMQ.
    
    Инкапсулирует данные сообщения и название очереди, в которую
    оно должно быть отправлено.
    """
    
    def __init__(self, data: dict, queue: str):
        """
        Инициализация сообщения.

        :param data: Словарь с данными сообщения
        :param queue: Имя очереди для отправки
        """
        self.data = data
        self.queue = queue

    def get_queue(self) -> str:
        """
        Получить имя очереди.
        
        :return: Имя очереди, в которую будет отправлено сообщение
        """
        return self.queue

    def get_data(self) -> dict:
        """
        Получить данные сообщения.
        
        :return: Словарь с данными сообщения
        """
        return self.data

    def set_data(self, data: dict) -> None:
        """
        Установить новые данные сообщения.
        
        :param data: Новый словарь с данными
        """
        self.data = data

    def set_queue(self, queue: str) -> None:
        """
        Установить новую очередь для сообщения.
        
        :param queue: Новое имя очереди
        """
        self.queue = queue
