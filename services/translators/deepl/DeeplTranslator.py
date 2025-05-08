from typing import Dict, Any
from services.translators.BaseTranslator import BaseTranslator
import requests
from config import (
    DEEPL_API_KEY,
    DEEPL_API_URL
)

class DeeplTranslator(BaseTranslator):
    """
    Реализация переводчика с использованием DeepL API.
    DeepL предоставляет высококачественный машинный перевод с поддержкой множества языков.
    
    Для работы требуется действительный API ключ DeepL, который должен быть указан
    в конфигурационном файле как DEEPL_API_KEY.
    
    Поддерживаемые языки и их коды можно найти в официальной документации DeepL:
    https://www.deepl.com/docs-api/translating-text/
    """
    def __init__(self):
        """
        Инициализация переводчика DeepL.
        Устанавливает API ключ и URL из конфигурации.
        """
        self.api_key = DEEPL_API_KEY
        self.api_url = DEEPL_API_URL

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполняет перевод текста через DeepL API.

        :param data: Словарь с данными для перевода:
            - text (str): текст для перевода
            - source_lang (str, опционально): исходный язык текста (например, 'EN', 'DE')
                Если не указан, DeepL автоматически определит язык
            - target_lang (str): целевой язык перевода (например, 'RU', 'FR')

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

        :raises: Не выбрасывает исключений, все ошибки обрабатываются и возвращаются в результате
        """
        text = data.get('text', '')
        source_lang = data.get('source_lang', '')
        target_lang = data.get('target_lang', '')
        
        if not text:
            return {"error": "No text provided"}
            
        if not target_lang:
            return {"error": "Target language not specified"}

        try:
            params = {
                "text": text,
                "target_lang": target_lang
            }
            
            if source_lang:
                params["source_lang"] = source_lang

            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"DeepL-Auth-Key {self.api_key}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data=params
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "translated_text": result['translations'][0]['text']
                }
            else:
                return {
                    "error": f"Translation failed with status code {response.status_code}",
                    "details": response.text
                }
        except Exception as e:
            return {
                "error": "Translation failed",
                "details": str(e)
            }
