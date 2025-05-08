import logging
import requests

from config import BOT_TOKEN, DEBUG_RECIPIENTS

class MessageSender:
    """
    Класс для отправки сообщений через Telegram бота.
    
    Использует Telegram Bot API для отправки сообщений указанным получателям.
    При возникновении ошибок отправляет уведомления об ошибках debug-получателям.
    """

    def __init__(self, token: str = BOT_TOKEN, recipients: list = DEBUG_RECIPIENTS):
        """
        Инициализация отправителя сообщений.

        Args:
            token (str): Токен Telegram бота. По умолчанию берется из конфигурации (BOT_TOKEN)
            recipients (list): Список получателей по умолчанию. По умолчанию берется из конфигурации (DEBUG_RECIPIENTS)
        """
        self.__token: str = token
        self.__recipients: list = recipients

    def send_message(self, message: str, recipients: list = None) -> None:
        """
        Отправка сообщения указанным получателям через Telegram бота.

        Args:
            message (str): Текст сообщения для отправки
            recipients (list, optional): Список получателей. 
                Если не указан, используется список по умолчанию из класса.

        Returns:
            None
        
        Note:
            В случае ошибки отправки сообщения конкретному получателю,
            отправляет уведомление об ошибке debug-получателям из конфигурации.
        """
        if recipients is None:
            recipients = self.get_recipients()

        for recipient in recipients:
            url = f"https://api.telegram.org/bot{self.get_token()}/sendMessage?chat_id={recipient}&text={message}"
            response = requests.get(url).json()

            if not response["ok"]:
                error_message = f"[services]->[telegram]->[send_message] Не удалось отправть сообщение получателю: '{recipient}', error: '{response['description']}', message: '{message}'"
                logging.error(error_message)
                self.send_message(error_message, DEBUG_RECIPIENTS)

    def get_token(self) -> str:
        """
        Получение токена бота.

        Returns:
            str: Токен Telegram бота
        """
        return self.__token

    def set_token(self, token: str):
        """
        Установка нового токена бота.

        Args:
            token (str): Новый токен Telegram бота
        """
        self.__token = token

    def get_recipients(self) -> list:
        """
        Получение списка получателей по умолчанию.

        Returns:
            list: Список получателей
        """
        return self.__recipients

    def set_recipients(self, recipients: list):
        """
        Установка нового списка получателей по умолчанию.

        Args:
            recipients (list): Новый список получателей
        """
        self.__recipients = recipients
