from typing import Dict, Any
from config import GOOGLE_API_KEY
from googletrans import Translator
from services.translators.BaseTranslator import BaseTranslator


class GoogleTranslator(BaseTranslator):
    """
    Реализация переводчика с использованием Google Translate API.
    Использует библиотеку googletrans для взаимодействия с сервисом перевода Google.
    
    Класс предоставляет возможность перевода текста с автоматическим определением
    языка источника или с явным указанием исходного языка.
    
    Примечание: В текущей реализации используется неофициальная библиотека googletrans,
    которая может иметь ограничения по сравнению с официальным Google Cloud Translation API.
    """

    def __init__(self):
        """
        Инициализация переводчика Google.
        Создает экземпляр переводчика и устанавливает API ключ из конфигурации.
        """
        self.translator = Translator()
        self.api_key = GOOGLE_API_KEY

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполняет перевод текста через Google Translate.

        :param data: Словарь с данными для перевода:
            - text (str): текст для перевода
            - source_lang (str, опционально): исходный язык текста.
                Если не указан, Google автоматически определит язык
            - target_lang (str): целевой язык перевода
                Коды языков должны быть в формате ISO-639-1 (например, 'en', 'ru', 'de')

        :return: Словарь с результатом:
            В случае успеха:
            {
                "success": True,
                "translated_text": "переведенный текст"
            }
            В случае ошибки:
            {
                "error": "описание ошибки",
                "details": "дополнительные детали ошибки"
            }

        Примечание: все исходные и целевые коды языков автоматически
        преобразуются в нижний регистр для совместимости с API.
        """
        text = data.get('text', '')
        source_lang = data.get('source_lang', '')
        target_lang = data.get('target_lang', '')
        
        if not text:
            return {"error": "No text provided"}
            
        if not target_lang:
            return {"error": "Target language not specified"}

        try:
            # Используем библиотеку googletrans для перевода
            result = self.translator.translate(
                text,
                src=source_lang.lower() if source_lang else None,
                dest=target_lang.lower()
            )
            
            return {
                "success": True,
                "translated_text": result.text
            }
        except Exception as e:
            return {
                "error": "Translation failed",
                "details": str(e)
            }
