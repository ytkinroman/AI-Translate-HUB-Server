import logging
from jsonrpcserver import Success, Error
from JSON_RPC.commands.base_command import BaseCommand
from services.telegram.send_message import MessageSender


class CmdTelegram(BaseCommand):
    def Execute(self, params: dict):
        try:
            payload = params.get('payload')
            command = payload.get('command')

            if not command:
                return Error(code=400, message="Command is required")

            #region << Отправка сообщения >>
            if command == "send_message":

                message_sender = MessageSender()

                message = payload.get("message")
                recipients = payload.get("recipients")

                if message:
                    message_sender.send_message(message, recipients)
                else:
                    return Error(code=400, message="Message is required")

                return Success(True)
            #endregion << Отправка сообщения >>
            else:
                return Error(code=400, message=f"Command '{command}' not found")
        except Exception as e:
            logging.error(f"[CMD_Transcribe] Error: {e}")
            return Error(code=500, message=str(e))
