from typing import Dict, Any
from modules.translators.BaseTranslater import BaseTranslator
from googletrans import Translator
from config import GOOGLE_API_KEY

class GoogleTranslator(BaseTranslator):
    def __init__(self):
        self.translator = Translator()
        self.api_key = GOOGLE_API_KEY

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        text = data.get('text', '')
        if not text:
            return {"error": "No text provided"}

        try:
            # Используем библиотеку googletrans для перевода
            result = self.translator.translate(
                text,
                src='en',
                dest='ru'
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

