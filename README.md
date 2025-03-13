# Сервер перевода текста

Сервер для перевода текста с использованием различных сервисов перевода (DeepL, Google, Yandex) через RabbitMQ с поддержкой WebSocket для получения результатов в реальном времени.

## Особенности

- Поддержка нескольких сервисов перевода (DeepL, Google, Yandex)
- Асинхронная обработка запросов через RabbitMQ
- WebSocket для получения результатов в реальном времени
- Поддержка нескольких воркеров для обработки запросов
- Масштабируемая архитектура
- Логирование всех операций

## Требования

- Python 3.8+
- RabbitMQ
- Доступ к API сервисов перевода (DeepL, Google, Yandex)

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd server
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/Mac
.venv\Scripts\activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `config.py` на основе `config.example.py` и заполните необходимые параметры:
```python
RMQ_USERNAME = "your_username"
RMQ_PASSWORD = "your_password"
```

## Запуск

1. Убедитесь, что RabbitMQ запущен и доступен

2. Запустите сервер:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000 --workers 4
```

Где:
- `--workers 4` - количество воркеров uvicorn (по умолчанию 4)
- `NUM_WORKERS=3` - количество RabbitMQ воркеров (можно установить через переменную окружения)

Пример запуска с настройкой количества RabbitMQ воркеров:
```bash
NUM_WORKERS=5 uvicorn app:app --reload --host 0.0.0.0 --port 8000 --workers 4
```

## API

### WebSocket Endpoint

1. Подключение к WebSocket:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

2. Получение ID сессии:
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'connection_established') {
        const sessionId = data.session_id;
        // Сохраните sessionId для использования в запросах
    }
};
```

### HTTP Endpoint

POST `/translate`

Тело запроса:
```json
{
    "text": "Текст для перевода",
    "translator_type": "deepl",  // или "google", "yandex"
    "ws_session_id": "полученный_session_id"
}
```

Ответ:
```json
{
    "status": "success",
    "message": "Translation request accepted"
}
```

## Архитектура

- FastAPI - основной веб-фреймворк
- RabbitMQ - очередь сообщений для обработки запросов
- WebSocket - для отправки результатов в реальном времени
- Множество воркеров для параллельной обработки запросов

## Логирование

Все операции логируются с использованием стандартного модуля logging Python. Логи содержат информацию о:
- Подключении к RabbitMQ
- Обработке сообщений
- Ошибках и проблемах
- Закрытии воркеров

## Безопасность

- Используйте HTTPS в продакшене
- Храните чувствительные данные (пароли, API ключи) в переменных окружения
- Настройте CORS в соответствии с вашими требованиями безопасности

## Лицензия

MIT