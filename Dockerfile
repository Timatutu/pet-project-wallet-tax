# Multi-stage build для оптимизации размера образа
FROM python:3.12-slim as builder

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Установка зависимостей Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Финальный образ
FROM python:3.12-slim

# Установка ngrok
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    && wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz \
    && tar -xvzf ngrok-v3-stable-linux-amd64.tgz -C /usr/local/bin \
    && rm ngrok-v3-stable-linux-amd64.tgz \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей из builder
COPY --from=builder /root/.local /root/.local

# Установка переменных окружения
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Создание рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY . .

# Создание директории для статических файлов
RUN mkdir -p /app/staticfiles

# Открытие портов
EXPOSE 8000 4040

# Скрипт запуска с ngrok
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Добавление whitenoise в middleware для статических файлов
ENV PYTHONPATH=/app

ENTRYPOINT ["/docker-entrypoint.sh"]

