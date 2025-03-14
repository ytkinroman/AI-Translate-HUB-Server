from typing import Dict, Any
from transformers import MarianMTModel, MarianTokenizer
import torch
from langdetect import detect
import langid
from BaseTranslater import BaseTranslator


class Translator(BaseTranslator):
    def __init__(self, device='cpu'):
        self.device = device

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        text = data['text']
        detected_lang = langid.classify(text)[0]
        target_lang = data['lang'].lower()[:2]
        model_name = f'Helsinki-NLP/opus-mt-{detected_lang}-{target_lang}'
        print(model_name)

        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name).to(self.device)

        # Токенизация текста
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.device)

        # Перевод текста
        with torch.no_grad():
            translated = model.generate(**inputs)

        # Декодирование переведенного текста
        translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)

        return {'text': translated_text, 'lang': detected_lang}

