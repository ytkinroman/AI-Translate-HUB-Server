from typing import Dict, Any
from modules.translators.BaseTranslater import BaseTranslator
import requests
from config import YANDEX_API_KEY

class YandexTranslator(BaseTranslator):
    def __init__(self):
        self.api_key = YANDEX_API_KEY
        self.detect_url = "https://translate.api.cloud.yandex.net/translate/v2/detect"
        self.translate_url = "https://translate.api.cloud.yandex.net/translate/v2/translate"

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        text = data.get('text', '')
        if not text:
            return {"error": "No text provided"}

        try:
            # Определяем язык исходного текста
            detect_response = requests.post(
                self.detect_url,
                headers={
                    "Authorization": f"Api-Key {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"text": text}
            )

            if detect_response.status_code != 200:
                return {
                    "error": "Language detection failed",
                    "details": detect_response.text
                }

            source_language = detect_response.json()['languageCode']

            # Выполняем перевод
            translate_response = requests.post(
                self.translate_url,
                headers={
                    "Authorization": f"Api-Key {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "texts": text,
                    "targetLanguageCode": "ru",
                    "sourceLanguageCode": source_language
                }
            )

            if translate_response.status_code == 200:
                result = translate_response.json()
                return {
                    "success": True,
                    "translated_text": result['translations'][0]['text'],
                    "source_language": source_language
                }
            else:
                return {
                    "error": f"Translation failed with status code {translate_response.status_code}",
                    "details": translate_response.text
                }
        except Exception as e:
            return {
                "error": "Translation failed",
                "details": str(e)
            }

