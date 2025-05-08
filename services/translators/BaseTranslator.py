from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTranslator(ABC):
    """
    Абстрактный базовый класс для всех сервисов перевода.
    Определяет общий интерфейс для всех конкретных реализаций переводчиков.
    """
    @abstractmethod
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполняет перевод текста с использованием конкретного сервиса перевода.

        :param data: Словарь с данными для перевода, содержащий:
            - text (str): исходный текст для перевода
            - source_lang (str, опционально): код языка исходного текста
            - target_lang (str): код языка, на который нужно перевести текст
            - additional_params (dict, опционально): дополнительные параметры для конкретного переводчика

        :return: Словарь с результатом перевода, содержащий:
            - translated_text (str): переведенный текст
            - source_lang (str): определенный язык исходного текста
            - target_lang (str): язык перевода
            - additional_info (dict, опционально): дополнительная информация от переводчика

        :raises TranslationError: в случае ошибки при переводе
        """
        pass
