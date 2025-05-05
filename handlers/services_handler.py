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
        Метод вызывает транскрибацию аудио

        :param context:  Экземпляр Worker
        :param payload:  {"jsonrpc": "2.0", "method": "transcribe", "params": {"payload": {"chat_id": "845512132", "file_path"}},"id": 1}
        :param method: Имя метода для вызова
        :return: Результат работы функции в формате JSON-строки
    """

    cmd_class_name = "TranslatorProvider"
    cmd = "services.translators." + cmd_class_name

    if context is None:
        logging.error("[RPC_Transcribe] Context (Worker instance) not provided to transcribe_audio")
        return Error(code=500, message="[RPC_Transcribe] Internal server error: Context not available")

    # Проверяем, есть ли пайплайн в контексте
    if not hasattr(context, 'transcribe_pipeline') or context.transcribe_pipeline is None:
        logging.error("[RPC_Transcribe] transcribe_pipeline not found or not initialized in context")
        return Error(code=500, message="[RPC_Transcribe] Internal server error: transcribe_pipeline not ready")

    try:
        params = dict()
        params['payload'] = payload
        logging.info(f"[RPC_Transcribe] Params: {params}")
        
        cmd_module = import_module(cmd)

        if hasattr(cmd_module, cmd_class_name):
            cmd_class = getattr(cmd_module, cmd_class_name)
            cmd_instance = cmd_class()

            result = cmd_instance.execute(params)
            
            if 'error' in result:
                logging.error(f"[RPC_Translate] Error: {result['error']}")
                return Error(code=500, message=result['error'])

            return Success(result)
        else:
            logging.error(f"[RPC_Transcribe] Command class {cmd_class_name} not found in module {cmd}")
            return Error(code=500, message=f"Command class {cmd_class_name} not found")

    except Exception as e:
        logging.error(f"[RPC_Transcribe] Error: {e}")
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

    cmd_class_name = "CmdTelegram"
    cmd = "JSON_RPC.commands.telegram"

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


@method
def parse_doc(context: object = None, payload: dict = {}):
    """
        Метод вызывает команду

        :param context:  Экземпляр Worker
        :param payload:  {"jsonrpc": "2.0", "method": "transcribe", "params": {"payload": {"chat_id": "845512132", "file_path"}},"id": 1}
        :param method: Имя метода для вызова
        :return: str: Результат работы функции в формате JSON-строки
    """

    cmd_class_name = "CmdParseDoc"
    cmd = "JSON_RPC.commands.parse_doc"

    # Проверяем, есть ли пайплайн в контексте
    if not hasattr(context, 'image_pipeline') or context.image_pipeline is None:
        logging.error("[RPC_Transcribe] image_pipeline not found or not initialized in context")
        return Error(code=500, message="[RPC_Transcribe] Internal server error: image_pipeline not ready")

    # Получаем пайплайн из контекста
    image_pipeline = context.image_pipeline

    try:
        params = dict()
        params['payload'] = payload
        params['pipeline'] = image_pipeline

        cmd_module = import_module(cmd)

        if hasattr(cmd_module, cmd_class_name):
            cmd_class = getattr(cmd_module, cmd_class_name)
            cmd_instance = cmd_class()

            result = cmd_instance.Execute(params)

            if type(result) == Error:
                logging.error(f"[RPC_Parse_doc] Error: {result.message}")

                _ = cmd_instance.Execute({"message": "Error: " + result.message, "command": "send_message"})

            return result
        else:
            logging.error(f"[RPC_Parse_doc] Command class {cmd_class_name} not found in module {cmd}")
            return Error(code=500, message=f"Command class {cmd_class_name} not found")

    except Exception as e:
        logging.error(f"[RPC_Parse_doc] Error: {e}")
        return Error(code=500, message=str(e))