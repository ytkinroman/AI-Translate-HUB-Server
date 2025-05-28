from typing import Dict
from fastapi import WebSocket

# Словарь для хранения активных WebSocket соединений
active_connections: Dict[str, WebSocket] = {}
