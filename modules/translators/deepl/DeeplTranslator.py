from typing import Dict, Any
from modules.translators.BaseTranslater import BaseTranslator
import requests
from config import DEEPL_API_KEY

class DeeplTranslator(BaseTranslator):
    def __init__(self):
        self.api_key = DEEPL_API_KEY
        self.api_url = "https://api-free.deepl.com/v2/translate"

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        text = data.get('text', '')
        if not text:
            return {"error": "No text provided"}

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"DeepL-Auth-Key {self.api_key}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "text": text,
                    "target_lang": "RU",
                    "source_lang": "EN"
                }
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

