from typing import Dict, Any
from services.translators.BaseTranslator import BaseTranslator
import requests
from config import (
    DEEPL_API_KEY,
    DEEPL_API_URL
)

class DeeplTranslator(BaseTranslator):
    def __init__(self):
        self.api_key = DEEPL_API_KEY
        self.api_url = DEEPL_API_URL

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

