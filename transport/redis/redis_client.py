import redis
import logging
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_TTL

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

def _get_websocket_key(connection_id: str) -> str:
    """Генерирует ключ для Redis"""
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
        logging.info(f"Storing connection ID: '{connection_id}'")
        redis_client.set(key, connection_id, ex=REDIS_TTL)
        return True
    except Exception as e:
        logging.error(f"Error storing connection ID: '{connection_id}'. Exception: {str(e)}")
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
        logging.info(f"Checking connection ID: '{connection_id}'")
        exists = redis_client.exists(key)
        if exists:
            logging.info(f"Connection ID exists")
            return True
        return False
    except Exception as e:
        logging.error(f"Error checking connection ID: '{connection_id}'. Exception: {str(e)}")
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
