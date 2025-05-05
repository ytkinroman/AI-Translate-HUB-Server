import logging
import requests

from config import BOT_TOKEN, DEBUG_RECIPIENTS


class MessageSender:
    def __init__(self, token: str = BOT_TOKEN, recipients: list = DEBUG_RECIPIENTS):
        self.__token: str = token
        self.__recipients: list = recipients

    def send_message(self, message: str, recipients: list = None) -> None:
        """
        Send a message to the specified recipients using the Telegram bot.
        :param message: Message to send.
        :param recipients: List of recipients. If None, use the default list from the class.
        :return: None
        """

        if recipients is None:
            recipients = self.get_recipients()

        for recipient in recipients:

            url = f"https://api.telegram.org/bot{self.get_token()}/sendMessage?chat_id={recipient}&text={message}"

            response = requests.get(url).json()

            if not response["ok"]:
                error_message = f"[services]->[telegram]->[send_message] Failed to send message to '{recipient}', error: '{response['description']}', message: '{message}'"
                logging.error(error_message)

                self.send_message(error_message, DEBUG_RECIPIENTS)

    def get_token(self) -> str:
        return self.__token

    def set_token(self, token: str):
        self.__token = token

    def get_recipients(self) -> list:
        return self.__recipients

    def set_recipients(self, recipients: list):
        self.__recipients = recipients