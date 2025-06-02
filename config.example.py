"""
Пример конфигурационного файла.

Для использования:
1. Скопируйте этот файл с именем config.py
2. Заполните все необходимые значения
3. Не добавляйте config.py в систему контроля версий

Все настройки разделены на логические секции для удобства конфигурации.
Каждая секция содержит связанные параметры с подробными комментариями.
"""

#region << Настройки подключения к RabbitMQ >>
# Настройки для подключения к серверу очередей RabbitMQ
# Для локальной разработки можно использовать значения по умолчанию
RMQ_USERNAME = "guest"  # Имя пользователя RabbitMQ
RMQ_PASSWORD = "guest"  # Пароль пользователя RabbitMQ
RMQ_HOST = "localhost"  # Хост RabbitMQ
RMQ_PORT = 5672        # Порт RabbitMQ (стандартный AMQP порт)
#endregion << Настройки подключения к RabbitMQ >>

#region << Настройки API ключей для сервисов перевода >>
# API ключи необходимы для работы с сервисами перевода
# Получить ключи можно в личных кабинетах соответствующих сервисов:
# DeepL: https://www.deepl.com/pro#developer
# Google: https://cloud.google.com/translate/docs/setup
# Yandex: https://cloud.yandex.ru/docs/translate/quickstart
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

#region <<  Настройки безопасности >>
CORS_ORIGINS = ["*"]  # Список разрешенных источников для CORS
MAX_CONNECTIONS = 100  # Максимальное количество одновременных WebSocket соединений
#endregion <<  Настройки безопасности >>

#region <<  Настройки API сервисов перевода >>
DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"
YANDEX_DETECT_URL = "https://translate.api.cloud.yandex.net/translate/v2/detect"
YANDEX_TRANSLATE_URL = "https://translate.api.cloud.yandex.net/translate/v2/translate" 
#endregion <<  Настройки API сервисов перевода >>

#region << Redis >>
# Настройки подключения к Redis
# Redis используется для хранения информации о WebSocket соединениях
# и кэширования часто запрашиваемых переводов
REDIS_HOST = "localhost"  # Хост Redis
REDIS_PORT = 6379        # Порт Redis
REDIS_DB = 0            # Номер базы данных Redis
REDIS_TTL = 3600        # Время жизни записей в Redis (в секундах)
#endregion << Redis >>

#region << FastAPI >>
APP_HOST = "localhost"  # Хост FastAPI сервера
APP_PORT = 8000        # Порт FastAPI сервера
#endregion << FastAPI >>

#region << Telegram >>
# Настройки для интеграции с Telegram ботом
BOT_TOKEN = ""  # Токен бота, полученный от @BotFather
DEBUG_RECIPIENTS = [""]  # Список ID пользователей для отправки отладочных сообщений
#endregion << Telegram >>

#region << ArdreygptTranslator >>
# Настройки для работы ArdreygptTranslator
ARDREYGPT_MODE = "local"  # Режим работы: "local" или "remote"
ARDREYGPT_REMOTE_URL = "http://localhost:5000/model_translate"  # URL удаленного сервера
ARDREYGPT_MODEL_WEIGHTS = None  # Путь к файлу с весами модели (опционально)
ARDREYGPT_TIMEOUT = 30  # Таймаут для запросов к удаленному серверу (в секундах)
ARDREYGPT_MODEL_NAME = "models_name"  # Директория для кэширования моделей
#endregion << ArdreygptTranslator >>

ALLOWED_TRANSLATORS = ['yandex', 'ardrey']
