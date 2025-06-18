#!/usr/bin/env python3
"""
Скрипт для проверки состояния кеша модели Hugging Face
"""

import os
import sys
from pathlib import Path
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from peft import PeftConfig
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_cache_path():
    """Получить путь к кешу Hugging Face"""
    default_cache = os.path.expanduser("~/.cache/huggingface/transformers")
    
    # Проверяем переменные окружения
    hf_cache = os.environ.get('HF_HOME', 
                             os.environ.get('HUGGINGFACE_HUB_CACHE', default_cache))
    return hf_cache

def check_model_cache(model_name):
    """Проверить состояние кеша для конкретной модели"""
    cache_path = get_cache_path()
    logger.info(f"Checking cache path: {cache_path}")
    
    # Различные возможные пути для модели
    possible_paths = [
        os.path.join(cache_path, f"models--{model_name.replace('/', '--')}"),
        os.path.join(cache_path, f"{model_name.replace('/', '--')}"),
        os.path.join(cache_path, model_name),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"✓ Found model cache at: {path}")
            
            # Проверяем содержимое
            files = []
            total_size = 0
            
            for root, dirs, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    try:
                        size = os.path.getsize(filepath)
                        total_size += size
                        files.append((filename, size))
                    except:
                        files.append((filename, "ERROR"))
            
            logger.info(f"Cache directory contains {len(files)} files")
            logger.info(f"Total cache size: {total_size / 1024 / 1024:.2f} MB")
            
            # Показываем важные файлы
            important_files = ['config.json', 'pytorch_model.bin', 'model.safetensors', 
                              'tokenizer_config.json', 'vocab.json']
            
            logger.info("Important files:")
            for filename, size in files:
                if any(imp in filename for imp in important_files):
                    if isinstance(size, int):
                        logger.info(f"  {filename}: {size / 1024 / 1024:.2f} MB")
                    else:
                        logger.info(f"  {filename}: {size}")
            
            return path, files, total_size
    
    logger.warning(f"✗ No cache found for model: {model_name}")
    return None, [], 0

def test_model_loading():
    """Тестирование загрузки модели"""
    model_name = "facebook/m2m100_418M"
    
    logger.info("=== Testing Model Loading ===")
    
    # Проверяем PEFT конфиг
    try:
        peft_config = PeftConfig.from_pretrained("./checkpoint-3900")
        base_model_name = peft_config.base_model_name_or_path
        logger.info(f"PEFT base model: {base_model_name}")
    except Exception as e:
        logger.error(f"Failed to load PEFT config: {e}")
        return False
    
    # Проверяем кеш
    cache_path, files, total_size = check_model_cache(base_model_name)
    
    if not cache_path:
        logger.warning("Model not found in cache - will need to download")
        return False
    
    # Пробуем загрузить из кеша
    try:
        logger.info("Testing tokenizer loading from cache...")
        tokenizer = M2M100Tokenizer.from_pretrained(
            base_model_name,
            local_files_only=True
        )
        logger.info("✓ Tokenizer loaded from cache successfully!")
        
        logger.info("Testing model loading from cache...")
        model = M2M100ForConditionalGeneration.from_pretrained(
            base_model_name,
            local_files_only=True,
            low_cpu_mem_usage=True,
            torch_dtype=torch.float32
        )
        logger.info("✓ Model loaded from cache successfully!")
        
        # Освобождаем память
        del model
        del tokenizer
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to load from cache: {e}")
        return False

def clear_cache(model_name):
    """Очистить кеш для конкретной модели"""
    cache_path, files, total_size = check_model_cache(model_name)
    
    if cache_path:
        import shutil
        logger.info(f"Clearing cache at: {cache_path}")
        try:
            shutil.rmtree(cache_path)
            logger.info("✓ Cache cleared successfully!")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    else:
        logger.info("No cache to clear")
        return True

def main():
    print("AI-Translate-HUB Cache Checker")
    print("=" * 50)
    
    # Проверяем общую информацию о кеше
    cache_path = get_cache_path()
    print(f"Cache directory: {cache_path}")
    print(f"Cache exists: {os.path.exists(cache_path)}")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--clear":
            model_name = "facebook/m2m100_418M"
            print(f"\n🗑️  Clearing cache for {model_name}")
            clear_cache(model_name)
            return
        elif sys.argv[1] == "--test":
            print("\n🧪 Testing model loading...")
            success = test_model_loading()
            if success:
                print("✅ All tests passed!")
            else:
                print("❌ Tests failed!")
            return
    
    # Проверяем состояние кеша
    model_name = "facebook/m2m100_418M"
    print(f"\n📁 Checking cache for model: {model_name}")
    
    cache_path, files, total_size = check_model_cache(model_name)
    
    if cache_path:
        print(f"✅ Cache found: {total_size / 1024 / 1024:.2f} MB")
        print("\nOptions:")
        print("  python check_cache.py --test    # Test loading from cache")
        print("  python check_cache.py --clear   # Clear cache")
    else:
        print("❌ No cache found - model will be downloaded on first run")

if __name__ == "__main__":
    import torch
    main()
