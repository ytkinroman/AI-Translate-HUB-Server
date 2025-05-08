import redis
import pickle
import logging
from fastapi import WebSocket
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_TTL
from transport.redis.serializable_websocket import SerializableWebSocket

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

def _get_websocket_key(connection_id: str) -> str:
    """Генерирует ключ для Redis"""
    return f"ws:{connection_id}"

def get_connection(connection_id: str) -> SerializableWebSocket:
    """
    Получает соединение из Redis по ID
    
    Args:
        connection_id: ID соединения
    
    Returns:
        SerializableWebSocket объект или None
    """
    try:
        key = _get_websocket_key(connection_id)
        value = redis_client.get(key)
        if value:
            return pickle.loads(value)
        return None
    except Exception:
        return None

def store_connection(connection_id: str, websocket: WebSocket) -> bool:
    """
    Сохраняет ID соединения в Redis
    
    Args:
        connection_id: ID соединения
        websocket: WebSocket объект
    
    Returns:
        bool: True если успешно сохранено
    """
    try:
        key = _get_websocket_key(connection_id)
        # Создаем сериализуемую версию WebSocket
        serializable_ws = SerializableWebSocket(websocket)
        # Сохраняем информацию о соединении с TTL
        pickled_object = pickle.dumps(serializable_ws)
        logging.info(f"Storing connection for ID: '{connection_id}'")
        redis_client.set(key, pickled_object, ex=REDIS_TTL)
        return True
    except Exception as e:
        logging.error(f"Error storing connection for ID: '{connection_id}'. Exception: {str(e)}")
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
        logging.info(f"Checking connection for ID: '{connection_id}'")
        value = redis_client.get(key)
        if value is not None:
            ws = pickle.loads(value)
            logging.info(f"Connection exists and can be deserialized")
            return True
        return False
    except Exception as e:
        logging.error(f"Error checking connection for ID: '{connection_id}'. Exception: {str(e)}")
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
