# Быстрый старт деплоя на Railway

## Шаги для деплоя

### 1. Подготовка репозитория
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push
```

### 2. Создание проекта на Railway

1. Зайдите на https://railway.app
2. Нажмите "New Project" → "Deploy from GitHub repo"
3. Выберите ваш репозиторий `pet-project-wallet-tax`
4. Railway автоматически обнаружит Dockerfile

### 3. Добавление PostgreSQL базы данных

1. В Railway dashboard нажмите "+ New"
2. Выберите "Database" → "Add PostgreSQL"
3. Railway автоматически создаст переменную `DATABASE_URL`

### 4. Настройка переменных окружения

В Railway dashboard → Variables добавьте:

```
SECRET_KEY=<сгенерируйте новый ключ>
DEBUG=False
ALLOWED_HOSTS=*.railway.app
USE_GUNICORN=true
ENVIRONMENT=Production
```

**Генерация SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Опционально: Ngrok для локальной разработки

Если нужен ngrok (для TON Connect локально):

```
NGROK_AUTHTOKEN=<ваш-ngrok-токен>
```

Получите токен: https://dashboard.ngrok.com/get-started/your-authtoken

### 6. Деплой

Railway автоматически запустит деплой после:
- Push в GitHub
- Изменения переменных окружения
- Нажатия "Deploy" вручную

### 7. Проверка

После деплоя:
- Railway предоставит публичный URL (например: `your-app.railway.app`)
- Проверьте доступность сайта
- Проверьте работу API: `https://your-app.railway.app/api/`

## Локальная разработка с Docker

```bash
# Сборка образа
docker build -t wallet-tax .

# Запуск с переменными окружения
docker run -p 8000:8000 \
  -e SECRET_KEY=your-dev-key \
  -e DEBUG=True \
  -e NGROK_AUTHTOKEN=your-ngrok-token \
  wallet-tax
```

Или с docker-compose:
```bash
# Создайте .env файл с переменными
cp .env.example .env
# Отредактируйте .env

# Запуск
docker-compose up
```

## Troubleshooting

### Ошибка: "No module named 'dj_database_url'"
- Убедитесь, что `requirements.txt` содержит `dj-database-url==2.1.0`

### Ошибка: "Static files not found"
- Проверьте, что `collectstatic` выполняется в docker-entrypoint.sh
- Убедитесь, что `STATIC_ROOT` настроен в settings.py

### Ngrok не запускается
- Проверьте, что `NGROK_AUTHTOKEN` установлен
- Проверьте логи: `docker logs <container-id>`

### База данных не подключается
- Проверьте, что PostgreSQL добавлен в Railway
- Убедитесь, что `DATABASE_URL` автоматически установлен Railway

