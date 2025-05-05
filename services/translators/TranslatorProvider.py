class TranslatorProvider:
    def __init__(self):
        pass
    
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
            translator = self.import_module(translator_class)
            translator_instance = translator()
            #endregion
            
            # Удаляем не нужный ключ
            params.pop("translator_code")
            
            # Выполняем перевод
            result = translator_instance.execute(params)
            
            return result
        except Exception as e:
            return {"error": f"Error: {str(e)}"}