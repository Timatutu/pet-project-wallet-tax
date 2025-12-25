# Деплой на Railway

## Подготовка к деплою

### 1. Настройка переменных окружения

В Railway добавьте следующие переменные окружения:

- `SECRET_KEY` - секретный ключ Django (сгенерируйте новый для production)
- `DEBUG=False` - отключите debug режим
- `ALLOWED_HOSTS=your-domain.railway.app,*.railway.app` - разрешенные хосты
- `NGROK_AUTHTOKEN` - токен ngrok (опционально, для локальной разработки)
- `USE_GUNICORN=true` - использовать gunicorn вместо runserver (рекомендуется для production)
- `DATABASE_URL` - Railway автоматически предоставляет эту переменную при добавлении PostgreSQL

### 2. Генерация SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Деплой на Railway

1. Подключите ваш GitHub репозиторий к Railway
2. Railway автоматически обнаружит `Dockerfile` и `railway.json`
3. Добавьте PostgreSQL базу данных через Railway dashboard
4. Настройте переменные окружения
5. Деплой запустится автоматически

### 4. Локальная разработка с Docker

```bash
# Сборка образа
docker build -t wallet-tax .

# Запуск с docker-compose (включая ngrok)
docker-compose up

# Или запуск только Django
docker run -p 8000:8000 -e SECRET_KEY=your-key -e DEBUG=True wallet-tax
```

### 5. Ngrok для TON Connect

Если нужен ngrok для локальной разработки с TON Connect:

1. Получите токен на https://dashboard.ngrok.com/get-started/your-authtoken
2. Добавьте `NGROK_AUTHTOKEN` в переменные окружения
3. Ngrok автоматически запустится и обновит `tonconnect-manifest.json`

### 6. Production настройки

В production рекомендуется:
- Использовать PostgreSQL (Railway предоставляет автоматически)
- Установить `USE_GUNICORN=true`
- Установить `DEBUG=False`
- Настроить `ALLOWED_HOSTS` с вашим доменом
- Использовать Railway's автоматический HTTPS

### 7. Проверка деплоя

После деплоя проверьте:
- Доступность сайта по Railway URL
- Работу API endpoints
- Статические файлы загружаются корректно
- База данных работает

## Структура файлов для деплоя

- `Dockerfile` - основной образ с Django и ngrok
- `docker-compose.yml` - для локальной разработки
- `docker-entrypoint.sh` - скрипт запуска
- `railway.json` - конфигурация Railway
- `.dockerignore` - исключения для Docker build
- `.env.example` - пример переменных окружения

