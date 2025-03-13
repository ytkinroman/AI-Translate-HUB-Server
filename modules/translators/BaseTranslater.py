from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTranslator(ABC):
    @abstractmethod
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполняет перевод текста
        :param data: Словарь с данными для перевода
        :return: Словарь с результатом перевода
        """
        pass
