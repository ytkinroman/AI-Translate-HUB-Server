from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTranslater(ABC):
    @abstractmethod
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполняет перевод текста
        :param data: Словарь с данными для перевода
        :return: Словарь с результатом перевода
        """
        pass
