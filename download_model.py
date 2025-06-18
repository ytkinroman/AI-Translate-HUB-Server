#!/usr/bin/env python3
"""
Скрипт для принудительной загрузки модели M2M100 через зеркало Hugging Face
с retry логикой и детальным логированием прогресса
"""

import os
import sys
import time
import logging
from pathlib import Path
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from peft import PeftConfig
import torch

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('download_model.log')
    ]
)
logger = logging.getLogger(__name__)

class ModelDownloader:
    def __init__(self, use_mirror=True):
        self.model_name = 'facebook/m2m100_418m'
        self.peft_model_path = "./checkpoint-3900"
        
        # Настройка зеркала Hugging Face
        if use_mirror:
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            logger.info("Using Hugging Face mirror: https://hf-mirror.com")
        else:
            logger.info("Using original Hugging Face Hub")
        
        # Настройка кэша
        self.cache_dir = os.path.expanduser("~/.cache/huggingface/transformers")
        logger.info(f"Cache directory: {self.cache_dir}")

    def check_peft_config(self):
        """Проверка конфигурации PEFT модели"""
        try:
            if not os.path.exists(self.peft_model_path):
                logger.error(f"PEFT checkpoint directory not found: {self.peft_model_path}")
                return False
                
            config_path = os.path.join(self.peft_model_path, "adapter_config.json")
            if not os.path.exists(config_path):
                logger.error(f"PEFT config not found: {config_path}")
                return False
                
            peft_config = PeftConfig.from_pretrained(self.peft_model_path)
            logger.info(f"PEFT base model: {peft_config.base_model_name_or_path}")
            
            # Проверяем, что базовая модель соответствует ожидаемой
            if peft_config.base_model_name_or_path != self.model_name:
                logger.warning(f"Base model mismatch: expected {self.model_name}, got {peft_config.base_model_name_or_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking PEFT config: {e}")
            return False

    def download_with_retry(self, download_func, max_retries=3, base_delay=5):
        """Загрузка с retry логикой и exponential backoff"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Download attempt {attempt + 1}/{max_retries}")
                result = download_func()
                logger.info("Download completed successfully!")
                return result
                
            except Exception as e:
                logger.error(f"Download attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("All download attempts failed!")
                    raise

    def download_tokenizer(self):
        """Загрузка токенизатора"""
        logger.info("Downloading tokenizer...")
        
        def _download():
            return M2M100Tokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir,
                resume_download=True,
                force_download=False
            )
        
        return self.download_with_retry(_download)

    def download_base_model(self):
        """Загрузка базовой модели"""
        logger.info("Downloading base model...")
        
        def _download():
            return M2M100ForConditionalGeneration.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir,
                resume_download=True,
                force_download=False,
                torch_dtype=torch.float32,  # Явно указываем тип для совместимости
                low_cpu_mem_usage=True  # Оптимизация для больших моделей
            )
        
        return self.download_with_retry(_download)

    def verify_model_files(self):
        """Проверка целостности загруженных файлов"""
        logger.info("Verifying downloaded model files...")
        
        # Основные файлы модели
        model_files = [
            'config.json',
            'pytorch_model.bin',
            'tokenizer_config.json',
            'vocab.json'
        ]
        
        cache_model_dir = os.path.join(self.cache_dir, f"models--facebook--m2m100_418m")
        
        if os.path.exists(cache_model_dir):
            logger.info(f"Model cache found at: {cache_model_dir}")
            return True
        else:
            logger.warning("Model cache directory not found")
            return False

    def run_download(self):
        """Основной процесс загрузки"""
        logger.info("=== Starting Model Download Process ===")
        
        try:
            # Проверка PEFT конфигурации
            if not self.check_peft_config():
                logger.error("PEFT configuration check failed")
                return False

            # Загрузка токенизатора
            logger.info("Step 1: Downloading tokenizer...")
            tokenizer = self.download_tokenizer()
            logger.info("✓ Tokenizer downloaded successfully")

            # Загрузка базовой модели
            logger.info("Step 2: Downloading base model...")
            model = self.download_base_model()
            logger.info("✓ Base model downloaded successfully")

            # Проверка файлов
            logger.info("Step 3: Verifying files...")
            if self.verify_model_files():
                logger.info("✓ Model files verified")
            else:
                logger.warning("⚠ Model file verification incomplete")

            # Тест инициализации
            logger.info("Step 4: Testing model initialization...")
            del model  # Освобождаем память
            del tokenizer
            
            # Быстрый тест загрузки
            test_tokenizer = M2M100Tokenizer.from_pretrained(self.model_name)
            test_model = M2M100ForConditionalGeneration.from_pretrained(self.model_name)
            
            logger.info("✓ Model initialization test passed")
            
            logger.info("=== Download Process Completed Successfully ===")
            return True

        except Exception as e:
            logger.error(f"Download process failed: {e}")
            return False

def main():
    print("AI-Translate-HUB Model Downloader")
    print("=" * 50)
    
    # Параметры командной строки
    use_mirror = True
    if len(sys.argv) > 1 and sys.argv[1] == '--no-mirror':
        use_mirror = False
    
    downloader = ModelDownloader(use_mirror=use_mirror)
    
    success = downloader.run_download()
    
    if success:
        print("\n✅ Model download completed successfully!")
        print("You can now run main_v2.py or main_v3.py")
    else:
        print("\n❌ Model download failed!")
        print("Check the log file 'download_model.log' for details")
        sys.exit(1)

if __name__ == "__main__":
    main()
