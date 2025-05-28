import logging
from config import ALLOWED_TRANSLATORS

class TranslatorProvider:
    """
    Провайдер сервисов перевода.
    
    Класс отвечает за:
    - Динамическую загрузку конкретных реализаций переводчиков
    - Управление процессом перевода
    - Обработку ошибок и логирование
    
    Поддерживает подключение различных сервисов перевода (Google, Yandex, DeepL)
    через единый интерфейс, обеспечивая гибкость в выборе сервиса перевода.
    """
    
    def __init__(self):
        """
        Инициализация провайдера переводчиков.
        """
        pass
    
    @staticmethod
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
    
    def execute(self, params: dict, context: object = None) -> dict:
        """
        Выполняет перевод текста с использованием указанного сервиса перевода.

        :param params: Параметры для выполнения перевода:
            - text (str): текст для перевода
            - target_lang (str): целевой язык перевода
            - translator_code (str): код переводчика ('google', 'yandex', 'deepl')
            - source_lang (str, опционально): исходный язык текста
            - additional_params (dict, опционально): дополнительные параметры

        :return: Словарь с результатом перевода или информацией об ошибке:
            В случае успеха: результат работы конкретного переводчика
            В случае ошибки: {"error": "описание ошибки"}

        :raises: Все исключения обрабатываются и возвращаются в виде словаря с ошибкой
        """
        try:
            result = None
            
            #region Получаем параметры из запроса
            
            text = params.get("text")
            target_lang = params.get("target_lang")
            translator_code = params.get("translator_code")
            
            logging.info(f"[TranslatorProvider] Received params: text='{text}', target_lang='{target_lang}', translator_code='{translator_code}'")
            
            #endregion
            
            #region Проверяем наличие необходимых параметров
            
            if not text:
                return {"error": "Нет текста для перевода"}
            
            if not target_lang:
                return {"error": "Целевой язык не указан"}
            
            if not translator_code:
                return {"error": "Не указан переводчик"}
            
            # Проверка на разрешенный переводчик
            if translator_code not in ALLOWED_TRANSLATORS:
                return {"error": f"Переводчик '{translator_code}' временно недоступен. Доступные переводчики: {', '.join(ALLOWED_TRANSLATORS)}"}
            
            #endregion
            
            #region Создаем экземпляр переводчика
            translator_class = f"services.translators.{translator_code}.{translator_code.capitalize()}Translator"
            translator = TranslatorProvider.import_module(translator_class)
            
            # Создаем экземпляр с учетом контекста
            if translator_code == 'ardrey' and context and hasattr(context, 'model'):
                translator_instance = translator(
                    model=context.model,
                    tokenizer=context.tokenizer,
                    device=context.device
                )
            else:
                translator_instance = translator()
            #endregion

            # Выполняем перевод
            logging.info(f"[TranslatorProvider] Executing translation with translator: {translator_class}")
            result = translator_instance.execute(params)
            logging.info(f"[TranslatorProvider] Translation result: {result}")
            
            return result
        except Exception as e:
            error_msg = f"Ошибка в TranslatorProvider: {str(e)}"
            logging.error(error_msg)
            return {"error": error_msg}
