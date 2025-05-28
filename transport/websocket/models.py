from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum


class MessageType(str, Enum):
    """Типы сообщений WebSocket."""
    
    # Системные сообщения
    CONNECTION_ESTABLISHED = "connection_established"
    ROOM_JOINED = "room_joined"
    ROOM_LEFT = "room_left"
    ROOM_OCCUPIED = "room_occupied"
    ERROR = "error"
    
    # Пользовательские сообщения
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    SEND_MESSAGE = "send_message"
    CHAT_MESSAGE = "chat_message"


class BaseMessage(BaseModel):
    """Базовая модель для всех WebSocket сообщений."""
    
    type: MessageType
    timestamp: Optional[float] = None


class JoinRoomMessage(BaseMessage):
    """Сообщение для присоединения к комнате."""
    
    type: MessageType = MessageType.JOIN_ROOM
    room_id: str = Field(..., description="Идентификатор комнаты")


class LeaveRoomMessage(BaseMessage):
    """Сообщение для выхода из комнаты."""
    
    type: MessageType = MessageType.LEAVE_ROOM


class SendMessage(BaseMessage):
    """Сообщение для отправки данных."""
    
    type: MessageType = MessageType.SEND_MESSAGE
    data: Dict[str, Any] = Field(..., description="Данные сообщения")
    target_room: Optional[str] = Field(None, description="Целевая комната (если не указана, отправляется в текущую комнату)")


class ConnectionEstablishedMessage(BaseMessage):
    """Ответ сервера при установке соединения."""
    
    type: MessageType = MessageType.CONNECTION_ESTABLISHED
    session_id: str = Field(..., description="Идентификатор сессии")
    room_id: Optional[str] = Field(None, description="Идентификатор персональной комнаты")


class RoomJoinedMessage(BaseMessage):
    """Ответ сервера при успешном присоединении к комнате."""
    
    type: MessageType = MessageType.ROOM_JOINED
    room_id: str = Field(..., description="Идентификатор комнаты")
    message: str = Field(default="Успешно присоединились к комнате")


class RoomLeftMessage(BaseMessage):
    """Ответ сервера при выходе из комнаты."""
    
    type: MessageType = MessageType.ROOM_LEFT
    room_id: str = Field(..., description="Идентификатор покинутой комнаты")
    message: str = Field(default="Покинули комнату")


class RoomOccupiedMessage(BaseMessage):
    """Ответ сервера если комната уже занята."""
    
    type: MessageType = MessageType.ROOM_OCCUPIED
    room_id: str = Field(..., description="Идентификатор занятой комнаты")
    message: str = Field(default="Комната уже занята")


class ErrorMessage(BaseMessage):
    """Сообщение об ошибке."""
    
    type: MessageType = MessageType.ERROR
    error_code: str = Field(..., description="Код ошибки")
    message: str = Field(..., description="Описание ошибки")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали ошибки")


class ChatMessage(BaseMessage):
    """Сообщение чата между пользователями."""
    
    type: MessageType = MessageType.CHAT_MESSAGE
    from_session: str = Field(..., description="ID отправителя")
    from_room: str = Field(..., description="Комната отправителя")
    message: str = Field(..., description="Текст сообщения")
    data: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")


# Маппинг типов сообщений к классам для парсинга
MESSAGE_TYPE_MAP = {
    MessageType.JOIN_ROOM: JoinRoomMessage,
    MessageType.LEAVE_ROOM: LeaveRoomMessage,
    MessageType.SEND_MESSAGE: SendMessage,
}
