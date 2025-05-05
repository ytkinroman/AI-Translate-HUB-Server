from typing import Dict, Any
from transformers import MarianMTModel, MarianTokenizer
import torch
import langid
from BaseTranslater import BaseTranslator


class Translator(BaseTranslator):
    def __init__(self, device='cpu'):
        self.device = device

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        text = data.get('text', '').strip()
        target_lang = data.get('target_lang', '').lower()[:2]

        if not text:
            return {"error": "No text provided"}

        if not target_lang:
            return {"error": "Target language not specified"}

        try:
            # Определяем язык исходного текста
            source_lang = langid.classify(text)[0]
            model_name = f'Helsinki-NLP/opus-mt-{source_lang}-{target_lang}'

            # Загружаем модель и токенизатор
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name).to(self.device)

            # Токенизация текста
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.device)

            # Перевод текста
            with torch.no_grad():
                translated = model.generate(**inputs)

            # Декодирование переведенного текста
            translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)

            return {
                "success": True,
                "translated_text": translated_text,
                "source_language": source_lang
            }
        except Exception as e:
            return {"error": "Translation failed", "details": str(e)}
