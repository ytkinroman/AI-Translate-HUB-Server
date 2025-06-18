"""
API endpoints для управления WebSocket комнатами.
"""

import logging
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from transport.websocket.room_manager import room_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rooms", tags=["WebSocket Rooms"])


class RoomInfo(BaseModel):
    """Информация о комнате."""
    room_id: str
    session_id: str
    is_occupied: bool


class RoomStats(BaseModel):
    """Статистика комнат."""
    total_connections: int
    total_rooms: int
    available_rooms: int
    occupied_rooms: List[RoomInfo]


@router.get("/stats", response_model=RoomStats)
async def get_room_stats():
    """
    Получить статистику по комнатам.
    
    Returns:
        RoomStats: Общая статистика и список занятых комнат
    """
    try:
        all_rooms = room_manager.get_all_rooms()
        occupied_rooms = [
            RoomInfo(
                room_id=room_id,
                session_id=session_id,
                is_occupied=True
            )
            for room_id, session_id in all_rooms.items()
        ]
        
        return RoomStats(
            total_connections=room_manager.get_total_connections(),
            total_rooms=room_manager.get_total_rooms(),
            available_rooms=float('inf'),  # Неограниченное количество доступных комнат
            occupied_rooms=occupied_rooms
        )
    except Exception as e:
        logger.error(f"Ошибка получения статистики комнат: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/check/{room_id}")
async def check_room_availability(room_id: str):
    """
    Проверить доступность комнаты.
    
    Args:
        room_id: Идентификатор комнаты
        
    Returns:
        Dict: Информация о доступности комнаты
    """
    try:
        is_available = room_manager.is_room_available(room_id)
        user_session = room_manager.get_room_user(room_id) if not is_available else None
        
        return {
            "room_id": room_id,
            "is_available": is_available,
            "is_occupied": not is_available,
            "occupant_session": user_session
        }
    except Exception as e:
        logger.error(f"Ошибка проверки комнаты {room_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/send/{room_id}")
async def send_message_to_room(room_id: str, message: Dict):
    """
    Отправить сообщение в комнату.
    
    Args:
        room_id: Идентификатор комнаты
        message: Сообщение для отправки
        
    Returns:
        Dict: Результат отправки
    """
    try:
        if not room_manager.get_room_user(room_id):
            raise HTTPException(status_code=404, detail=f"Комната {room_id} пуста")
        
        success = await room_manager.send_to_room(room_id, message)
        
        if success:
            return {
                "success": True,
                "message": f"Сообщение отправлено в комнату {room_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="Не удалось отправить сообщение")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в комнату {room_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.delete("/kick/{session_id}")
async def kick_user_from_room(session_id: str):
    """
    Принудительно отключить пользователя от комнаты.
    
    Args:
        session_id: Идентификатор сессии пользователя
        
    Returns:
        Dict: Результат операции
    """
    try:
        room_id = room_manager.leave_room(session_id)
        
        if room_id:
            return {
                "success": True,
                "message": f"Пользователь {session_id} отключен от комнаты {room_id}"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Пользователь {session_id} не найден в комнатах")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка отключения пользователя {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
