import uuid
import logging
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from transport.redis.redis_client import store_connection, remove_connection
from config import MAX_CONNECTIONS
from . import active_connections
from transport.websocket.room_manager import room_manager
from transport.websocket.models import (
    MessageType, 
    MESSAGE_TYPE_MAP,
    ConnectionEstablishedMessage,
    RoomJoinedMessage,
    RoomLeftMessage,
    RoomOccupiedMessage,
    ErrorMessage
)

# Настройка логирования
logger = logging.getLogger(__name__)

router = APIRouter()


async def handle_client_message(websocket: WebSocket, session_id: str, data: Dict[str, Any]):
    """
    Обрабатывает сообщения от клиента.
    
    Args:
        websocket: WebSocket соединение
        session_id: ID сессии клиента
        data: Данные сообщения
    """
    try:
        # Получаем тип сообщения
        message_type = data.get("type")
        if not message_type:
            await websocket.send_json(ErrorMessage(
                error_code="MISSING_MESSAGE_TYPE",
                message="Тип сообщения не указан"
            ).dict())
            return
        
        # Валидируем тип сообщения
        if message_type not in MESSAGE_TYPE_MAP:
            await websocket.send_json(ErrorMessage(
                error_code="UNKNOWN_MESSAGE_TYPE", 
                message=f"Неизвестный тип сообщения: {message_type}"
            ).dict())
            return
        
        # Парсим сообщение
        message_class = MESSAGE_TYPE_MAP[message_type]
        try:
            message = message_class(**data)
        except Exception as e:
            await websocket.send_json(ErrorMessage(
                error_code="INVALID_MESSAGE_FORMAT",
                message=f"Неверный формат сообщения: {str(e)}"
            ).dict())
            return
        
        # Обрабатываем сообщение в зависимости от типа
        if message_type == MessageType.SEND_MESSAGE:
            await handle_send_message(websocket, session_id, message.data, message.target_room)
        
        elif message_type == MessageType.JOIN_ROOM:
            # Присоединение к комнате теперь недоступно - у каждого своя персональная комната
            await websocket.send_json(ErrorMessage(
                error_code="OPERATION_NOT_ALLOWED",
                message="Присоединение к комнатам отключено. У каждого пользователя есть персональная комната."
            ).dict())
        
        elif message_type == MessageType.LEAVE_ROOM:
            # Выход из комнаты недоступен - пользователь всегда находится в своей персональной комнате
            await websocket.send_json(ErrorMessage(
                error_code="OPERATION_NOT_ALLOWED", 
                message="Выход из персональной комнаты невозможен."
            ).dict())
        
        else:
            await websocket.send_json(ErrorMessage(
                error_code="UNHANDLED_MESSAGE_TYPE",
                message=f"Обработчик для типа {message_type} не реализован"
            ).dict())
            
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения от сессии {session_id}: {str(e)}")
        await websocket.send_json(ErrorMessage(
            error_code="INTERNAL_ERROR",
            message="Внутренняя ошибка сервера"
        ).dict())


async def handle_join_room(websocket: WebSocket, session_id: str, room_id: str):
    """
    Обрабатывает присоединение к комнате.
    """
    if room_manager.join_room(room_id, session_id, websocket):
        await websocket.send_json(RoomJoinedMessage(
            room_id=room_id,
            timestamp=time.time()
        ).dict())
        logger.info(f"Сессия {session_id} присоединилась к комнате {room_id}")
    else:
        await websocket.send_json(RoomOccupiedMessage(
            room_id=room_id,
            timestamp=time.time()
        ).dict())
        logger.warning(f"Сессия {session_id} не смогла присоединиться к занятой комнате {room_id}")


async def handle_leave_room(websocket: WebSocket, session_id: str):
    """
    Обрабатывает выход из комнаты.
    """
    room_id = room_manager.leave_room(session_id)
    if room_id:
        await websocket.send_json(RoomLeftMessage(
            room_id=room_id,
            timestamp=time.time()
        ).dict())
        logger.info(f"Сессия {session_id} покинула комнату {room_id}")
    else:
        await websocket.send_json(ErrorMessage(
            error_code="NOT_IN_ROOM",
            message="Вы не находитесь в комнате"
        ).dict())


async def handle_send_message(websocket: WebSocket, session_id: str, data: Dict[str, Any], target_room: str = None):
    """
    Обрабатывает отправку сообщения.
    """
    # Если целевая комната не указана, используем текущую комнату пользователя
    if not target_room:
        target_room = room_manager.get_user_room(session_id)
        if not target_room:
            await websocket.send_json(ErrorMessage(
                error_code="NOT_IN_ROOM",
                message="Вы не находитесь в комнате"
            ).dict())
            return
    
    # Отправляем сообщение в комнату
    success = await room_manager.send_to_room(target_room, {
        "type": MessageType.CHAT_MESSAGE,
        "from_session": session_id,
        "from_room": room_manager.get_user_room(session_id),
        "message": "Пользовательские данные",
        "data": data,
        "timestamp": time.time()
    })
    
    if not success:
        await websocket.send_json(ErrorMessage(
            error_code="SEND_FAILED",
            message=f"Не удалось отправить сообщение в комнату {target_room}"
        ).dict())


@router.websocket("/ws/{room_id}")
async def websocket_endpoint_with_room(websocket: WebSocket, room_id: str):
    """
    Endpoint для WebSocket с автоматическим присоединением к комнате через URL.
    
    Args:
        websocket: Входящее WebSocket соединение
        room_id: Идентификатор комнаты из URL
    """
    # Проверяем лимит подключений
    if len(active_connections) >= MAX_CONNECTIONS:
        await websocket.close(code=1008, reason="Достигнут лимит подключений")
        return

    # Проверяем доступность комнаты
    if not room_manager.is_room_available(room_id):
        await websocket.close(code=1008, reason=f"Комната {room_id} уже занята")
        return

    await websocket.accept()
    
    # Генерируем UUID для сессии
    session_id = str(uuid.uuid4())
    
    try:
        # Сохраняем websocket локально и id в Redis
        active_connections[session_id] = websocket
        store_connection(session_id)

        # Присоединяем к комнате
        if not room_manager.join_room(room_id, session_id, websocket):
            await websocket.close(code=1008, reason=f"Не удалось присоединиться к комнате {room_id}")
            return        # Отправляем подтверждение соединения
        
        # Отправляем подтверждение присоединения к комнате
        await websocket.send_json(RoomJoinedMessage(
            room_id=room_id,
            timestamp=time.time()
        ).dict())
        
        # Обрабатываем входящие сообщения
        while True:
            data = await websocket.receive_json()
            await handle_client_message(websocket, session_id, data)
            
    except WebSocketDisconnect:
        logger.info(f"Соединение закрыто для сессии {session_id}")
    except Exception as e:
        logger.error(f"Ошибка в websocket_endpoint для сессии {session_id}: {str(e)}")
    finally:
        # Очищаем ресурсы при любом типе отключения
        logger.info(f"Удаление сессии {session_id}")
        if session_id in active_connections:
            del active_connections[session_id]
        remove_connection(session_id)
        room_manager.leave_room(session_id)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: Optional[str] = Query(None)):
    """
    Основной endpoint для WebSocket с автоматическим созданием персональной комнаты.
    Сервер автоматически создает комнату room_{session_id} для каждого пользователя.
    
    Args:
        websocket: Входящее WebSocket соединение
        client_id: Опциональный client_id для переподключений
    """
    # Проверяем лимит подключений
    if len(active_connections) >= MAX_CONNECTIONS:
        await websocket.close(code=1008, reason="Достигнут лимит подключений")
        return

    await websocket.accept()
    
    # Если client_id передан и валиден, используем его
    if client_id and client_id.strip():
        session_id = client_id
        logger.info(f"Используется переданный client_id: {session_id}")
        
        # Обработка коллизий - если ID уже активен, закрываем старое соединение
        if session_id in active_connections:
            logger.warning(f"Client_id {session_id} уже активен, закрываем старое соединение")
            old_websocket = active_connections[session_id]
            try:
                await old_websocket.close(code=1008, reason="Новое подключение с тем же client_id")
            except:
                pass
    else:
        # Генерируем новый ID для первого подключения
        session_id = str(uuid.uuid4())
        logger.info(f"Сгенерирован новый session_id: {session_id}")
    
    # Создаем персональную комнату на основе session_id
    personal_room_id = f"room_{session_id}"
    
    try:
        # Сохраняем websocket локально и id в Redis
        active_connections[session_id] = websocket
        store_connection(session_id)

        # Автоматически присоединяем к персональной комнате
        # Поскольку комната создается на основе уникального session_id, 
        # конфликтов быть не может
        if not room_manager.join_room(personal_room_id, session_id, websocket):
            await websocket.close(code=1008, reason="Не удалось создать персональную комнату")
            return        # Отправляем подтверждение соединения с информацией о комнате
        
        # Отправляем подтверждение присоединения к персональной комнате
        await websocket.send_json(RoomJoinedMessage(
            room_id=personal_room_id,
            timestamp=time.time()
        ).dict())
        
        logger.info(f"Сессия {session_id} создала и присоединилась к персональной комнате {personal_room_id}")
        
        # Обрабатываем входящие сообщения
        while True:
            data = await websocket.receive_json()
            await handle_client_message(websocket, session_id, data)
            
    except WebSocketDisconnect:
        logger.info(f"Соединение закрыто для сессии {session_id}")
    except Exception as e:
        logger.error(f"Ошибка в websocket_endpoint для сессии {session_id}: {str(e)}")
    finally:
        # Очищаем ресурсы при любом типе отключения
        logger.info(f"Удаление сессии {session_id} и комнаты {personal_room_id}")
        if session_id in active_connections:
            del active_connections[session_id]
        remove_connection(session_id)
        room_manager.leave_room(session_id)
