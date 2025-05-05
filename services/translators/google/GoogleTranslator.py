from typing import Dict, Any
from config import GOOGLE_API_KEY
from googletrans import Translator
from services.translators.BaseTranslator import BaseTranslator


class GoogleTranslator(BaseTranslator):
    def __init__(self):
        self.translator = Translator()
        self.api_key = GOOGLE_API_KEY

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

