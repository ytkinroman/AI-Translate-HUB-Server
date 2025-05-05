import redis
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

def store_connection(connection_id: str, websocket) -> bool:
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
        # Сохраняем информацию о соединении с TTL
        redis_client.set(key, "1", ex=REDIS_TTL)
        return True
    except Exception:
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
        return bool(redis_client.get(key))
    except Exception:
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
