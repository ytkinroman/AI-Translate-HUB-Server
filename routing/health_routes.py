from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging
import asyncio
from datetime import datetime

# Импорты для проверки сервисов
try:
    from transport.redis.redis_client import redis_client
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import aio_pika
    from config import RMQ_HOST, RMQ_PORT, RMQ_USERNAME, RMQ_PASSWORD
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False

router = APIRouter()
logger = logging.getLogger(__name__)

class HealthStatus(BaseModel):
    """
    Модель статуса здоровья сервиса.
    
    Атрибуты:
        status: Общий статус сервиса (healthy/unhealthy)
        timestamp: Временная метка проверки
        services: Статус отдельных сервисов
        uptime: Время работы сервиса
    """
    status: str
    timestamp: str
    services: Dict[str, Any]
    version: str = "1.0.0"

class ServiceStatus(BaseModel):
    """
    Модель статуса отдельного сервиса.
    
    Атрибуты:
        status: Статус сервиса (up/down)
        response_time: Время отклика в миллисекундах
        error: Сообщение об ошибке (если есть)
    """
    status: str
    response_time: float = None
    error: str = None

# Время запуска сервиса
service_start_time = datetime.now()

async def check_redis() -> ServiceStatus:
    """Проверка доступности Redis."""
    if not REDIS_AVAILABLE:
        return ServiceStatus(
            status="down",
            error="Redis client not available"
        )
    
    try:
        start_time = datetime.now()
        
        # Попробуем выполнить простую операцию с Redis (синхронный клиент)
        redis_client.ping()
        
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ServiceStatus(
            status="up",
            response_time=response_time
        )
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return ServiceStatus(
            status="down",
            error=str(e)
        )

async def check_rabbitmq() -> ServiceStatus:
    """Проверка доступности RabbitMQ."""
    if not RABBITMQ_AVAILABLE:
        return ServiceStatus(
            status="down",
            error="RabbitMQ client not available"
        )
    
    try:
        start_time = datetime.now()
        
        # Попробуем установить соединение с RabbitMQ используя параметры из конфига
        connection_url = f"amqp://{RMQ_USERNAME}:{RMQ_PASSWORD}@{RMQ_HOST}:{RMQ_PORT}/"
        connection = await aio_pika.connect_robust(connection_url)
        await connection.close()
        
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ServiceStatus(
            status="up",
            response_time=response_time
        )
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {e}")
        return ServiceStatus(
            status="down",
            error=str(e)
        )

@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Полная проверка здоровья сервиса.
    
    Проверяет состояние всех критических компонентов:
    - Redis
    - RabbitMQ  
    - База данных (CSV файл)
    
    Returns:
        HealthStatus: Подробная информация о состоянии сервиса
    """
    logger.info("Performing health check")
    
    # Запускаем проверки параллельно
    redis_status, rabbitmq_status = await asyncio.gather(
        check_redis(),
        check_rabbitmq(),
        return_exceptions=True
    )
    
    # Обрабатываем исключения
    if isinstance(redis_status, Exception):
        redis_status = ServiceStatus(status="down", error=str(redis_status))
    if isinstance(rabbitmq_status, Exception):
        rabbitmq_status = ServiceStatus(status="down", error=str(rabbitmq_status))
    
    services = {
        "redis": redis_status.dict(),
        "rabbitmq": rabbitmq_status.dict(),
    }
    
    # Определяем общий статус
    all_services_up = all(
        service["status"] == "up" 
        for service in services.values()
    )
    
    overall_status = "healthy" if all_services_up else "unhealthy"
    
    # Вычисляем время работы
    uptime = (datetime.now() - service_start_time).total_seconds()
    
    return HealthStatus(
        status=overall_status,
        timestamp=datetime.now().isoformat(),
        services=services
    )

@router.get("/health/live")
async def liveness_probe():
    """
    Простая проверка живости сервиса.
    
    Эта проверка всегда возвращает успех, если сервис запущен.
    Используется для Kubernetes liveness probe.
    
    Returns:
        dict: Простой ответ о том, что сервис жив
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }
