#!/bin/bash
set -e

# Ожидание готовности базы данных
echo "Waiting for database..."
sleep 2

# Применение миграций
echo "Running migrations..."
python manage.py migrate --noinput

# Создание суперпользователя если нужно (только для первого запуска)
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput --email "$DJANGO_SUPERUSER_EMAIL" || true
fi

# Сборка статических файлов
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Определение команды запуска
if [ "$USE_GUNICORN" = "true" ] || [ -z "$NGROK_AUTHTOKEN" ]; then
    # Production режим с gunicorn
    echo "Starting Gunicorn server..."
    exec gunicorn wallet.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
else
    # Development режим с runserver и ngrok
    echo "Starting Django development server..."
    python manage.py runserver 0.0.0.0:8000 &
    DJANGO_PID=$!
    
    # Ожидание запуска Django
    sleep 3
    
    # Запуск ngrok
    if [ -n "$NGROK_AUTHTOKEN" ]; then
        echo "Starting ngrok..."
        ngrok config add-authtoken "$NGROK_AUTHTOKEN" || true
        ngrok http 8000 --log=stdout &
        NGROK_PID=$!
        
        # Получение публичного URL от ngrok
        sleep 5
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        
        if [ -n "$NGROK_URL" ]; then
            echo "=========================================="
            echo "Ngrok tunnel is running!"
            echo "Public URL: $NGROK_URL"
            echo "=========================================="
            
            # Обновление manifest.json для TON Connect если нужно
            if [ -f "wallet_nalog/static/tonconnect-manifest.json" ]; then
                sed -i "s|\"url\": \".*\"|\"url\": \"$NGROK_URL\"|g" wallet_nalog/static/tonconnect-manifest.json || true
                echo "Updated tonconnect-manifest.json with ngrok URL"
            fi
        fi
        
        # Ожидание завершения процессов
        wait $NGROK_PID $DJANGO_PID
    else
        wait $DJANGO_PID
    fi
fi

