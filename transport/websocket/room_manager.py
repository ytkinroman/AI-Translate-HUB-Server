import logging
from typing import Dict, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class RoomManager:
    """
    Менеджер комнат для WebSocket соединений.
    
    Особенности:
    - Максимум 1 пользователь на комнату
    - Автоматическое освобождение комнат при отключении
    - Проверка доступности комнат перед присоединением
    """
    
    def __init__(self):
        # Маппинг: room_id -> session_id
        self._rooms: Dict[str, str] = {}
        
        # Маппинг: session_id -> room_id (для быстрого поиска)
        self._session_to_room: Dict[str, str] = {}
        
        # Хранение WebSocket соединений: session_id -> WebSocket
        self._connections: Dict[str, WebSocket] = {}
    
    def is_room_available(self, room_id: str) -> bool:
        """
        Проверяет, доступна ли комната для присоединения.
        
        Args:
            room_id: Идентификатор комнаты
            
        Returns:
            bool: True если комната свободна, False если занята
        """
        return room_id not in self._rooms
    
    def join_room(self, room_id: str, session_id: str, websocket: WebSocket) -> bool:
        """
        Присоединяет пользователя к комнате.
        
        Args:
            room_id: Идентификатор комнаты
            session_id: Идентификатор сессии пользователя
            websocket: WebSocket соединение
            
        Returns:
            bool: True если успешно присоединился, False если комната занята
        """
        if not self.is_room_available(room_id):
            logger.warning(f"Попытка присоединения к занятой комнате {room_id} от сессии {session_id}")
            return False
        
        # Если пользователь уже в другой комнате, отключаем его от неё
        if session_id in self._session_to_room:
            old_room_id = self._session_to_room[session_id]
            self.leave_room(session_id)
            logger.info(f"Пользователь {session_id} покинул комнату {old_room_id}")
        
        # Присоединяем к новой комнате
        self._rooms[room_id] = session_id
        self._session_to_room[session_id] = room_id
        self._connections[session_id] = websocket
        
        logger.info(f"Пользователь {session_id} присоединился к комнате {room_id}")
        return True
    
    def leave_room(self, session_id: str) -> Optional[str]:
        """
        Отключает пользователя от комнаты.
        
        Args:
            session_id: Идентификатор сессии пользователя
            
        Returns:
            Optional[str]: ID покинутой комнаты или None если пользователь не был в комнате
        """
        if session_id not in self._session_to_room:
            return None
        
        room_id = self._session_to_room[session_id]
        
        # Удаляем из всех структур данных
        del self._rooms[room_id]
        del self._session_to_room[session_id]
        if session_id in self._connections:
            del self._connections[session_id]
        
        logger.info(f"Пользователь {session_id} покинул комнату {room_id}")
        return room_id
    
    def get_user_room(self, session_id: str) -> Optional[str]:
        """
        Получает ID комнаты, в которой находится пользователь.
        
        Args:
            session_id: Идентификатор сессии пользователя
            
        Returns:
            Optional[str]: ID комнаты или None если пользователь не в комнате
        """
        return self._session_to_room.get(session_id)
    
    def get_room_user(self, room_id: str) -> Optional[str]:
        """
        Получает ID пользователя в комнате.
        
        Args:
            room_id: Идентификатор комнаты
            
        Returns:
            Optional[str]: ID пользователя или None если комната пуста
        """
        return self._rooms.get(room_id)
    
    def get_websocket(self, session_id: str) -> Optional[WebSocket]:
        """
        Получает WebSocket соединение пользователя.
        
        Args:
            session_id: Идентификатор сессии пользователя
            
        Returns:
            Optional[WebSocket]: WebSocket соединение или None если не найдено
        """
        return self._connections.get(session_id)
    
    async def send_to_room(self, room_id: str, message: dict) -> bool:
        """
        Отправляет сообщение в комнату (единственному пользователю в ней).
        
        Args:
            room_id: Идентификатор комнаты
            message: Сообщение для отправки (словарь, будет сериализован в JSON)
            
        Returns:
            bool: True если сообщение отправлено, False если комната пуста или ошибка
        """
        session_id = self.get_room_user(room_id)
        if not session_id:
            logger.warning(f"Попытка отправки сообщения в пустую комнату {room_id}")
            return False
        
        websocket = self.get_websocket(session_id)
        if not websocket:
            logger.error(f"WebSocket соединение не найдено для сессии {session_id}")
            return False
        
        try:
            await websocket.send_json(message)
            logger.debug(f"Сообщение отправлено в комнату {room_id} (сессия {session_id})")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в комнату {room_id}: {str(e)}")
            return False
    
    async def send_to_user(self, session_id: str, message: dict) -> bool:
        """
        Отправляет сообщение конкретному пользователю.
        
        Args:
            session_id: Идентификатор сессии пользователя
            message: Сообщение для отправки (словарь, будет сериализован в JSON)
            
        Returns:
            bool: True если сообщение отправлено, False если пользователь не найден или ошибка
        """
        websocket = self.get_websocket(session_id)
        if not websocket:
            logger.warning(f"WebSocket соединение не найдено для сессии {session_id}")
            return False
        
        try:
            await websocket.send_json(message)
            logger.debug(f"Сообщение отправлено пользователю {session_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {session_id}: {str(e)}")
            return False
    
    def get_all_rooms(self) -> Dict[str, str]:
        """
        Получает информацию о всех активных комнатах.
        
        Returns:
            Dict[str, str]: Словарь {room_id: session_id}
        """
        return self._rooms.copy()
    
    def get_total_connections(self) -> int:
        """
        Получает общее количество активных соединений.
        
        Returns:
            int: Количество активных соединений
        """
        return len(self._connections)
    
    def get_total_rooms(self) -> int:
        """
        Получает общее количество занятых комнат.
        
        Returns:
            int: Количество занятых комнат
        """
        return len(self._rooms)


# Глобальный экземпляр менеджера комнат
room_manager = RoomManager()
