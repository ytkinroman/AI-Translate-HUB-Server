import logging
from jsonrpcserver import method, Success, Error


def import_module(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

@method
def translate(context: object, payload: dict):
    """
        Метод вызывает переводчик текста

        :param context: Экземпляр Worker
        :param payload: {"jsonrpc": "2.0", "method": "translate", "params": {"payload": {"text": "Hello", "target_lang": "??ru??", "translator_code": "yandex", "source_lang": "en"},"id": 1}
        :param method: Имя метода для вызова
        :return: Результат работы функции в формате JSON-строки
    """

    cmd_class_name = "TranslatorProvider"
    cmd = "services.translators." + cmd_class_name

    if context is None:
        logging.error("[RPC_Translate] Контекст (Экземпляр воркера) не укзан")
        return Error(code=500, message="[RPC_Translate] Internal server error: Контекст (Экземпляр воркера) не укзан")

    try:
        params = dict(payload.get('params')).get('payload')
        if not params:
            logging.error("[RPC_Translate] Не указаны параметры для перевода")
            return Error(code=500, message="[RPC_Translate] Internal server error: Не указаны параметры для перевода")
        
        logging.info(f"[RPC_Translate] Параметры: {params}")
        
        cmd_module = import_module(cmd)

        if hasattr(cmd_module, cmd_class_name):
            cmd_class = getattr(cmd_module, cmd_class_name)
            cmd_instance = cmd_class()

            result = cmd_instance.execute(params)
            
            if 'error' in result:
                logging.error(f"[RPC_Translate] Ошибка: {result['error']}")
                return Error(code=500, message=result['error'])

            return Success(result)
        else:
            logging.error(f"[RPC_Translate] Класс переводчика {cmd_class_name} не найден в модуле {cmd}")
            return Error(code=500, message=f"Класс переводчика {cmd} не найден")

    except Exception as e:
        logging.error(f"[RPC_Translate] Ошибка: {str(e)}")
        return Error(code=500, message=str(e))

@method
def telegram(context: object = None, payload: dict = {}):
    """
        Метод вызывает команду Telegram

        :param context:  Экземпляр Worker
        :param payload:  {"jsonrpc": "2.0", "method": "transcribe", "params": {"payload": {"chat_id": "845512132", "file_path"}},"id": 1}
        :param method: Имя метода для вызова
        :return: str: Результат работы функции в формате JSON-строки
    """

    cmd_class_name = "TelegramProvider"
    cmd = "services.telegram.TelegramProvider"

    try:
        params = dict()
        params['payload'] = payload

        cmd_module = import_module(cmd)

        if hasattr(cmd_module, cmd_class_name):
            cmd_class = getattr(cmd_module, cmd_class_name)
            cmd_instance = cmd_class()

            result = cmd_instance.Execute(params)

            if type(result) == Error:
                logging.error(f"[RPC_Telegram] Error: {result.message}")

                _ = cmd_instance.Execute({"message": "Error: " + result.message, "command": "send_message"})

            return result
        else:
            logging.error(f"[RPC_Telegram] Command class {cmd_class_name} not found in module {cmd}")
            return Error(code=500, message=f"Command class {cmd_class_name} not found")

    except Exception as e:
        logging.error(f"[RPC_Telegram] Error: {e}")
        return Error(code=500, message=str(e))
