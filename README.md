# Сервер перевода текста

Серверное приложение для асинхронного перевода текста с использованием различных сервисов перевода (DeepL, Google, Yandex). Взаимодействие между компонентами осуществляется через RabbitMQ, а получение результатов происходит в реальном времени через WebSocket соединение.

## Основные возможности

- Интеграция с DeepL, Google Translate, Yandex.Translate.
- Асинхронная обработка запросов через RabbitMQ.
- Получение результатов в реальном времени через WebSocket.
- Горизонтальное масштабирование.
- Отказоустойчивость.
- Подробное логирование.
- Опциональная интеграция с Telegram ботом.

## Системные требования

- Python 3.12+
- RabbitMQ 3.12+
- Redis 7.2+
- API ключи для сервисов перевода (DeepL, Google, Yandex).

## Установка и настройка

1.  Клонируйте репозиторий:
    ```bash
    git clone <repository-url>
    cd trans-server
    ```
2.  Создайте и активируйте виртуальное окружение:
    ```bash
    python -m venv .venv
    # Linux/macOS:
    source .venv/bin/activate
    # Windows:
    .venv\Scripts\activate
    ```
3.  Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```
4.  Настройка конфигурации:
    - Скопируйте `config.example.py` в `config.py`.
    - Заполните `config.py`: API ключи, параметры RabbitMQ и Redis.

## Установка и настройка зависимых сервисов (Docker)

### Redis
```bash
docker run -d --name redis -p 6379:6379 -v redis_data:/data --restart unless-stopped redis:7.2
```

### RabbitMQ
```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=your_secure_password --restart unless-stopped rabbitmq:3.12-management
```
Веб-интерфейс RabbitMQ: http://localhost:15672

## Запуск сервера

1.  Убедитесь, что Docker контейнеры запущены.
2.  Запустите основной сервер:
    ```bash
    uvicorn app:app --reload --host 0.0.0.0 --port 8000
    ```
3.  Запустите обработчик запросов на перевод:
    ```bash
    python -m handlers.request_handler
    ```
4.  Запустите обработчик результатов перевода:
    ```bash
    python -m handlers.result_handler
    ```

## API Кратко

### WebSocket API
- **Endpoint**: `ws://localhost:8000/ws`
- Сервер автоматически создает персональную комнату для каждого пользователя.
- Сообщения: `connection_established`, `room_joined`, `chat_message`, `translation_result`, `error`.

### HTTP API

**Перевод текста:**
```http
POST /translate
Content-Type: application/json

{
    "text": "Текст для перевода",
    "translator_type": "deepl",
    "target_lang": "ru",
    "ws_session_id": "id_сессии_websocket"
}
```
Ответ: `{"status": "success", "message": "Запрос на перевод принят"}`

## Лицензия

MIT
