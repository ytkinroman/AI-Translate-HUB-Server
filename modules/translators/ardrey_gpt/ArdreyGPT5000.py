import torch
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from langdetect import detect
from typing import Dict, Any
from modules.translators.BaseTranslator import BaseTranslator

class M2M100Translator(BaseTranslator):
    """
    Реализация переводчика с использованием модели M2M100_418M из transformers.
    Поддерживает автоматическое определение языка исходного текста.
    """
    def __init__(self, weights_path: str = None):
        super().__init__()
        self.model_name = 'facebook/m2m100_418m'
        self.tokenizer = M2M100Tokenizer.from_pretrained(self.model_name)
        self.model = M2M100ForConditionalGeneration.from_pretrained(self.model_name)

        # Загружаем собственные веса, если указаны
        if weights_path:
            try:
                check_point = torch.load(weights_path)
                if isinstance(check_point, dict) and 'state_dict' in check_point:
                    self.model.load_state_dict(check_point['state_dict'])
                else:
                    print('Путь к весам не содержит правильный state_dict.')
            except Exception as e:
                print(f'Ошибка загрузки весов: {e}')

        # Переносим модель на доступное устройство
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(device)
        self.device = device  # сохраним для удобства

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        text = data.get('text', '')
        source_lang = data.get('source_lang')  # Может быть None
        target_lang = data.get('target_lang', '').lower()

        if not text:
            return {"error": "Не предоставлен текст для перевода"}

        if not target_lang:
            return {"error": "Не указан целевой язык перевода"}

        try:
            # Определение исходного языка, если не указан
            if not source_lang:
                source_lang = self.detect_language(text)
                if not source_lang:
                    return {"error": "Не удалось определить язык исходного текста"}

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

            return {
                "result": {
                    "success": True,
                    "text": translated_text,
                    "source_language": source_lang
                }
            }
        except Exception as e:
            return {
                "error": "Ошибка при выполнении перевода",
                "details": str(e)
            }

    def detect_language(self, text: str) -> str:
        """
        Определение языка по тексту с помощью langdetect.
        Возвращает код языка или пустую строку при ошибке.
        """
        try:
            lang_code = detect(text)
            return lang_code
        except ImportError:
            # Если langdetect не установлен
            print("Библиотека langdetect не установлена.")
            return ""
        except Exception as e:
            print(f"Ошибка определения языка: {e}")
            return ""