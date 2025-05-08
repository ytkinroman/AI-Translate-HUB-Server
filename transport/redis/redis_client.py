import redis
import logging
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_TTL

"""
Модуль для работы с Redis.

Предоставляет функционал для:
- Хранения информации об активных WebSocket соединениях
- Управления временем жизни соединений
- Проверки существования соединений

Использует Redis для временного хранения данных с автоматическим
удалением по истечении TTL (Time To Live).
"""

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

def _get_websocket_key(connection_id: str) -> str:
    """
    Генерирует ключ для хранения в Redis.
    
    :param connection_id: ID WebSocket соединения
    :return: Ключ в формате 'ws:{connection_id}'
    """
    return f"ws:{connection_id}"

def store_connection(connection_id: str) -> bool:
    """
    Сохраняет ID соединения в Redis
    
    Args:
        connection_id: ID соединения
    
    Returns:
        bool: True если успешно сохранено
    """
    try:
        key = _get_websocket_key(connection_id)
        logging.info(f"Сохранение ID соединения: '{connection_id}'")
        redis_client.set(key, connection_id, ex=REDIS_TTL)
        return True
    except Exception as e:
        logging.error(f"Ошибка при сохранении ID соединения: '{connection_id}'. Исключение: {str(e)}")
        return False

def check_connection(connection_id: str) -> bool:
    """
    Проверяет существование соединения в Redis
    
    Args:
        connection_id: ID соединения
    
    Returns:
        bool: True если соединение существует
    """
    try:
        key = _get_websocket_key(connection_id)
        logging.info(f"Проверка ID соединения: '{connection_id}'")
        exists = redis_client.exists(key)
        if exists:
            logging.info(f"ID соединения существует")
            return True
        return False
    except Exception as e:
        logging.error(f"Ошибка при проверке ID соединения: '{connection_id}'. Исключение: {str(e)}")
        return False

def remove_connection(connection_id: str) -> bool:
    """
    Удаляет соединение из Redis
    
    Args:
        connection_id: ID соединения
    
    Returns:
        bool: True если успешно удалено
    """
    try:
        key = _get_websocket_key(connection_id)
        redis_client.delete(key)
        return True
    except Exception:
        return False
