import logging
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

class SerializableWebSocket:
    """
    Класс-обертка для WebSocket, который можно сериализовать
    """
    def __init__(self, websocket: WebSocket):
        self._ws = websocket
        
    async def send_json(self, data: dict):
        """Отправляет JSON-данные через WebSocket"""
        try:
            await self._ws.send_json(data)
            return True
        except Exception as e:
            logging.error(f"Error sending data through WebSocket: {str(e)}")
            return False
            
    def __getstate__(self):
        """Определяет, какие данные сохранять при сериализации"""
        return {
            'client_state': self._ws.client_state.value,
            'application_state': self._ws.application_state.value
        }
        
    def __setstate__(self, state):
        """Восстанавливает объект при десериализации"""
        self._state = state
    def get_ws(self) -> WebSocket:
        """Возвращает оригинальный WebSocket объект"""
        return self._ws
