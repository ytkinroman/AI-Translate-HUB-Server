from services.telegram.MessageSender import MessageSender


class TelegramProvider: 
    def execute(self, params: dict) -> dict:
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
                    return {"error": "Message is required"}

                return {"result": {"status": True}}
            else:
                return {"error": f"Command '{command}' not found"}
            
        except Exception as e:
            return{"error": str(e)}