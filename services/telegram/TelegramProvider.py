from services.telegram.MessageSender import MessageSender

class TelegramProvider: 
    """
    Провайдер для работы с Telegram сервисом.
    Обрабатывает команды для отправки сообщений через Telegram бота.

    Поддерживаемые команды:
    - send_message: Отправка сообщения указанным получателям
    """
    def execute(self, params: dict) -> dict:
        """
        Выполняет команду для работы с Telegram сервисом.

        Args:
            params (dict): Словарь с параметрами команды.
                Обязательные поля:
                - payload (dict): Содержит данные для выполнения команды
                    - command (str): Название команды
                    Для команды send_message:
                    - message (str): Текст сообщения
                    - recipients (list, optional): Список получателей

        Returns:
            dict: Результат выполнения команды
                В случае успеха:
                    {"result": {"status": True}}
                В случае ошибки:
                    {"error": str} - текст ошибки
        """
        try:
            payload = params.get('payload')
            command = payload.get('command')

            if not command:
                return {"error": "Не указана команда"}
            
            if command == "send_message":

                message_sender = MessageSender()

                message = payload.get("message")
                recipients = payload.get("recipients")

                if message:
                    message_sender.send_message(message, recipients)
                else:
                    return {"error": "Не указано сообщение для отправки"}

                return {"result": {"status": True}}
            else:
                return {"error": f"Команда '{command}' не найдена"}
            
        except Exception as e:
            return{"error": str(e)}
