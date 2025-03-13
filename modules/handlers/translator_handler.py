import importlib
from typing import Dict, Any


class TranslatorHandler:
    def __init__(self):
        self.translators: Dict[str, str] = {
            "deepl": "modules.translators.deepl.DeeplTranslator",
            "google": "modules.translators.google.GoogleTranslator",
            "yandex": "modules.translators.yandex.YandexTranslator"
        }

    def handle_translation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        translator_type = data.get('type')
        if translator_type not in self.translators:
            return {"error": f"Translator {translator_type} not found"}

        try:
            # Динамически импортируем и создаем экземпляр переводчика
            module_path, class_name = self.translators[translator_type].rsplit('.', 1)
            module = importlib.import_module(module_path)
            translator_class = getattr(module, class_name)
            translator = translator_class()
            
            return translator.execute(data)
        except Exception as e:
            return {
                "error": f"Failed to initialize translator {translator_type}",
                "details": str(e)
            } 