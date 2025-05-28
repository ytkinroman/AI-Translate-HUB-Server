import logging
from jsonrpcserver import method, Success, Error


def import_module(name: str) -> object:
    """
    Динамически импортирует модуль по его полному имени.

    :param name: Полное имя модуля в формате 'package.subpackage.module'
    :return: Импортированный модуль
    :raises ImportError: если модуль не может быть импортирован
    """
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

@method
def translate(context: object, payload: dict):
    """
    RPC метод для выполнения перевода текста.
    
    Создает экземпляр соответствующего переводчика и выполняет перевод
    с указанными параметрами. Поддерживает все доступные сервисы перевода
    (Google, Yandex, DeepL).

    :param context: Экземпляр обработчика запросов
    :param payload: Параметры для перевода:
        {
            "text": str,          # текст для перевода
            "target_lang": str,   # целевой язык перевода
            "translator_code": str,# код переводчика (yandex/google/deepl)
            "source_lang": str    # исходный язык (опционально)
        }
    :return: В случае успеха - объект Success с результатом перевода
             В случае ошибки - объект Error с описанием проблемы
    """

    cmd_class_name = "TranslatorProvider"
    cmd = "services.translators." + cmd_class_name

    if context is None:
        logging.error("[RPC_Translate] Контекст (Экземпляр воркера) не укзан")
        return Error(code=500, message="[RPC_Translate] Internal server error: Контекст (Экземпляр воркера) не укзан")

    try:
        if not payload:
            logging.error(f"[RPC_Translate] Не указаны параметры для перевода: '{payload}'")
            return Error(code=500, message="[RPC_Translate] Internal server error: Не указаны параметры для перевода")
        
        logging.info(f"[RPC_Translate] Параметры: {payload}")
        
        cmd_module = import_module(cmd)
        if hasattr(cmd_module, cmd_class_name):
            cmd_class = getattr(cmd_module, cmd_class_name)
            cmd_instance = cmd_class()
            result = cmd_instance.execute(payload, context=context)
            
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
    RPC метод для обработки команд Telegram.
    
    Обрабатывает входящие команды от Telegram бота и возвращает
    соответствующий результат через API Telegram.

    :param context: Экземпляр обработчика запросов
    :param payload: Параметры команды в формате:
        {
            "chat_id": str,    # ID чата для ответа
            "command": str,    # команда для выполнения
            "text": str,       # текст сообщения (опционально)
            "file_path": str   # путь к файлу (опционально)
        }
    :return: В случае успеха - объект Success с результатом выполнения команды
             В случае ошибки - объект Error с описанием проблемы
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
                logging.error(f"[RPC_Telegram] Ошибка: {result.message}")
                _ = cmd_instance.Execute({"message": "Ошибка: " + result.message, "command": "send_message"})

            return result
        else:
            logging.error(f"[RPC_Telegram] Класс обработчика {cmd_class_name} не найден в модуле {cmd}")
            return Error(code=500, message=f"Класс обработчика {cmd_class_name} не найден")

    except Exception as e:
        logging.error(f"[RPC_Telegram] Ошибка: {e}")
        return Error(code=500, message=f"Внутренняя ошибка сервера: {str(e)}")
