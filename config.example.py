#region << Настройки подключения к RabbitMQ >>
RMQ_USERNAME = "guest"  # Имя пользователя RabbitMQ
RMQ_PASSWORD = "guest"  # Пароль пользователя RabbitMQ
RMQ_HOST = "localhost"  # Хост RabbitMQ
RMQ_PORT = 5672        # Порт RabbitMQ (стандартный AMQP порт)
#endregion << Настройки подключения к RabbitMQ >>

#region << Настройки API ключей для сервисов перевода >>
DEEPL_API_KEY = "your-deepl-api-key"  # API ключ DeepL
GOOGLE_API_KEY = "your-google-api-key"  # API ключ Google Translate
YANDEX_API_KEY = "your-yandex-api-key"  # API ключ Yandex.Translate
#endregion << Настройки API ключей для сервисов перевода >>

#region <<  Настройки очередей RabbitMQ >>
TRANSLATION_QUEUE = "translation_requests"  # Имя очереди для запросов на перевод
RESULT_QUEUE = "translation_results"        # Имя очереди для результатов перевода
#endregion <<  Настройки очередей RabbitMQ >>

#region <<  Настройки логирования >>
LOG_LEVEL = "INFO"  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # Формат логов
#endregion <<  Настройки логирования >>

#region <<  Настройки WebSocket >>
WS_PING_INTERVAL = 10  # Интервал пинга WebSocket соединения в секундах
WS_PING_TIMEOUT = 22   # Таймаут ожидания ответа на пинг в секундах
#endregion <<  Настройки WebSocket >>

#region <<  Настройки безопасности >>
CORS_ORIGINS = ["*"]  # Список разрешенных источников для CORS
MAX_CONNECTIONS = 100  # Максимальное количество одновременных WebSocket соединений
#endregion <<  Настройки безопасности >>

#region <<  Настройки API сервисов перевода >>
DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"
YANDEX_DETECT_URL = "https://translate.api.cloud.yandex.net/translate/v2/detect"
YANDEX_TRANSLATE_URL = "https://translate.api.cloud.yandex.net/translate/v2/translate" 
#endregion <<  Настройки API сервисов перевода >>