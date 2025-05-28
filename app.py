import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import (
    LOG_LEVEL, 
    LOG_FORMAT,
    CORS_ORIGINS
)

from routing.config_routes import router as config_router
from routing.translation_routes import router as translation_router
from routing.websocket_routes import router as websocket_router
from routing.health_routes import router as health_router
from routing.room_routes import router as room_router

"""
Основной модуль FastAPI приложения.

Обеспечивает:
- WebSocket подключения для real-time коммуникации
- HTTP endpoints для получения запросов на перевод
- Обработку результатов перевода
- Мониторинг активных соединений
- Механизм проверки активности соединений (ping/pong)
"""

# Настройка логирования
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(config_router)
app.include_router(translation_router)
app.include_router(websocket_router)
app.include_router(health_router)
app.include_router(room_router)
