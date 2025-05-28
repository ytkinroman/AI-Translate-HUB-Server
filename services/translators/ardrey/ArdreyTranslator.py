import requests
import logging
from typing import Dict, Any
from langdetect import detect
from services.translators.BaseTranslator import BaseTranslator

from config import (
    ARDREYGPT_MODE,
    ARDREYGPT_REMOTE_URL,
    ARDREYGPT_MODEL_WEIGHTS,
    ARDREYGPT_TIMEOUT
)

class ArdreyTranslator(BaseTranslator):
    """
    Реализация переводчика с использованием модели M2M100.
    Поддерживает два режима работы:
    1. Локальный - использует модель напрямую на сервере
    2. Удаленный - отправляет запросы на удаленный сервер с моделью
    """
    def __init__(self, model=None, tokenizer=None, device=None):
        """
        Инициализация переводчика в зависимости от режима работы.
        В локальном режиме использует предоставленную модель.
        В удаленном режиме настраивает параметры подключения к серверу.

        :param model: Предварительно загруженная модель M2M100
        :param tokenizer: Предварительно загруженный токенизатор M2M100
        :param device: Устройство для выполнения вычислений (cuda/cpu)
        """
        self.mode = ARDREYGPT_MODE
        if self.mode == "local":
            self.model = model
            self.tokenizer = tokenizer
            self.device = device
            logging.info(f"[ArdreyTranslator] Initialized in local mode using shared model instance")
        else:
            self.remote_url = ARDREYGPT_REMOTE_URL
            self.timeout = ARDREYGPT_TIMEOUT
            logging.info(f"[ArdreyTranslator] Initialized in remote mode with URL: {self.remote_url}")

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполняет перевод текста в зависимости от режима работы.
        
        :param data: Словарь с параметрами:
            - text: исходный текст
            - source_lang: исходный язык (опционально)
            - target_lang: целевой язык
            
        :return: Словарь с результатом перевода или ошибкой
        """
        text = data.get('text', '')
        source_lang = data.get('source_lang')
        target_lang = data.get('target_lang', '')

        logging.info(f"[ArdreyTranslator] Received translation request: "
                    f"text='{text}', source_lang='{source_lang}', target_lang='{target_lang}'")

        if not text:
            return {"error": "Не предоставлен текст для перевода"}

        if not target_lang:
            return {"error": "Не указан целевой язык перевода"}

        try:
            # Определяем язык если не указан
            if source_lang is None or source_lang == '':
                source_lang = self.detect_language(text)
                if not source_lang:
                    return {"error": "Не удалось определить язык исходного текста"}
                logging.info(f"[ArdreyTranslator] Detected source language: {source_lang}")

            # Выполняем перевод в зависимости от режима
            if self.mode == "local":
                return self._translate_local(text, source_lang, target_lang)
            else:
                return self._translate_remote(text, source_lang, target_lang)

        except Exception as e:
            logging.error(f"[ArdreyTranslator] Translation error: {e}")
            return {
                "error": "Ошибка при выполнении перевода",
                "details": str(e)
            }

    def _translate_local(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """
        Выполняет перевод локально используя предоставленную модель M2M100.
        """
        if not all([self.model, self.tokenizer, self.device]):
            error_msg = "Model not properly initialized"
            logging.error(f"[ArdreyTranslator] {error_msg}")
            return {"error": error_msg}
        """
        Выполняет перевод локально используя модель M2M100.
        """
        try:
            # Установка языка источника
            self.tokenizer.src_lang = source_lang

            # Токенизация входного текста
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)

            # Генерация перевода
            generated_tokens = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.get_lang_id(target_lang)
            )

            # Декодирование результата
            translated_text = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]

            logging.info(f"[ArdreyTranslator] Local translation successful")
            return {
                "result": {
                    "success": True,
                    "text": translated_text,
                    "source_language": source_lang
                }
            }
        except Exception as e:
            logging.error(f"[ArdreyTranslator] Local translation error: {e}")
            raise

    def _translate_remote(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """
        Отправляет запрос на перевод удаленному серверу.
        """
        try:
            response = requests.post(
                self.remote_url,
                json={
                    "text": text,
                    "source_lang": source_lang,
                    "target_lang": target_lang
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                logging.info(f"[ArdreyTranslator] Remote translation successful")
                return result
            else:
                error_msg = f"Remote translation failed with status code: {response.status_code}"
                logging.error(f"[ArdreyTranslator] {error_msg}")
                return {
                    "error": error_msg,
                    "details": response.text
                }
        except requests.Timeout:
            error_msg = f"Timeout connecting to remote translation server"
            logging.error(f"[ArdreyTranslator] {error_msg}")
            return {"error": error_msg}
        except requests.RequestException as e:
            error_msg = f"Error connecting to remote translation server: {str(e)}"
            logging.error(f"[ArdreyTranslator] {error_msg}")
            return {"error": error_msg}
        except Exception as e:
            logging.error(f"[ArdreyTranslator] Remote translation error: {e}")
            raise

    def detect_language(self, text: str) -> str:
        """
        Определяет язык текста используя langdetect.
        
        :param text: Текст для определения языка
        :return: Код языка или пустую строку при ошибке
        """
        try:
            return detect(text)
        except Exception as e:
            logging.error(f"[ArdreyTranslator] Language detection error: {e}")
            return ""
