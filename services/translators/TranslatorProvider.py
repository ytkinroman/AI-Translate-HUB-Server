import logging

class TranslatorProvider:
    def __init__(self):
        pass
    
    @staticmethod
    def import_module(name):
        components = name.split('.')
        mod = __import__(components[0])
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod
    
    def execute(self, params: dict) -> dict:
        """
        Метод вызывает команду перевода текста
        :param params: Параметры для выполнения команды
        :return: Результат работы функции в формате JSON-строки
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
            
            #endregion
            
            #region Импортируем класс переводчика
            translator_class = f"services.translators.{translator_code}.{translator_code.capitalize()}Translator"
            translator = TranslatorProvider.import_module(translator_class)
            translator_instance = translator()
            #endregion
            
            # Выполняем перевод
            logging.info(f"[TranslatorProvider] Executing translation with translator: {translator_class}")
            result = translator_instance.execute(params)
            logging.info(f"[TranslatorProvider] Translation result: {result}")
            
            return result
        except Exception as e:
            error_msg = f"Error in TranslatorProvider: {str(e)}"
            logging.error(error_msg)
            return {"error": error_msg}
