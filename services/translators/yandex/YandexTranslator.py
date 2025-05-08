import requests
import logging
from typing import Dict, Any
from services.translators.BaseTranslator import BaseTranslator

from config import (
    YANDEX_API_KEY,
    YANDEX_DETECT_URL,
    YANDEX_TRANSLATE_URL
)


class YandexTranslator(BaseTranslator):
    """API клиент Yandex переводчика."""
    def __init__(self):
        self.api_key = YANDEX_API_KEY
        self.detect_url = YANDEX_DETECT_URL
        self.translate_url = YANDEX_TRANSLATE_URL

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        text = data.get('text', '')
        source_lang = data.get('source_lang')  # Убираем значение по умолчанию
        target_lang = data.get('target_lang', '')
        
        logging.info(f"[YandexTranslator] Received params: text='{text}', source_lang='{source_lang}', target_lang='{target_lang}'")
        
        if not text:
            return {"error": "No text provided"}
            
        if not target_lang:
            return {"error": "Target language not specified"}

        try:
            # Определяем язык исходного текста, если не указан или равен None
            if source_lang is None or source_lang == '':
                logging.info("[YandexTranslator] Source language not specified, detecting language...")
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

                source_lang = detect_response.json()['languageCode']
                logging.info(f"[YandexTranslator] Detected source language: {source_lang}")

            # Выполняем перевод
            translate_response = requests.post(
                self.translate_url,
                headers={
                    "Authorization": f"Api-Key {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "texts": text,
                    "targetLanguageCode": target_lang.lower(),
                    "sourceLanguageCode": source_lang.lower()
                }
            )

            if translate_response.status_code == 200:
                result = translate_response.json()
                logging.info(f"[YandexTranslator] Translation successful: {result}")
                return {
                    "result": {
                        "success": True,
                        "text": result['translations'][0]['text'],
                        "source_language": source_lang
                    }
                }
            else:
                return {
                    "error": f"Перевод не выполнился с кодом: '{translate_response.status_code}'",
                    "details": translate_response.text
                }
        except Exception as e:
            return {
                "error": "Ошибка при выполнении перевода",
                "details": str(e)
            }
