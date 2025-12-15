# Настройка TON Connect для локальной разработки (Windows)

## Проблема
Tonkeeper требует HTTPS для загрузки манифеста. При локальной разработке на `http://localhost:8000` манифест не загружается.

## ⚠️ ВАЖНО: Если ngrok блокирует ваш IP

Если вы видите ошибку `ERR_NGROK_9040` или "We do not allow agents to connect to ngrok from your IP address", используйте **localtunnel** (см. раздел ниже) - он не блокирует IP адреса и не требует регистрации!

## Решение: ngrok

### Шаг 1: Регистрация в ngrok (бесплатно)

1. Перейдите на сайт: https://dashboard.ngrok.com/signup
2. Зарегистрируйтесь (можно через Google/GitHub)
3. После регистрации перейдите: https://dashboard.ngrok.com/get-started/your-authtoken
4. Скопируйте ваш authtoken (длинная строка типа `2abc123...xyz`)

### Шаг 2: Скачайте и настройте ngrok

1. Скачайте ngrok для Windows: https://ngrok.com/download
2. Распакуйте архив в любую папку (например, `C:\ngrok`)
3. Откройте PowerShell или Command Prompt
4. Перейдите в папку с ngrok.exe:
   ```powershell
   cd C:\ngrok
   ```
5. Установите authtoken (замените `ВАШ_AUTHTOKEN` на реальный токен):
   ```powershell
   .\ngrok.exe config add-authtoken ВАШ_AUTHTOKEN
   ```
   Например:
   ```powershell
   .\ngrok.exe config add-authtoken 2abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
   ```

### Шаг 3: Запустите Django сервер

Откройте PowerShell или Command Prompt и перейдите в папку проекта:
```powershell
cd C:\wallet_project\wallet
```

Активируйте виртуальное окружение (если используете):
```powershell
.venv\Scripts\activate
```

Запустите Django сервер:
```powershell
python manage.py runserver
```

**Оставьте этот терминал открытым!** Сервер должен работать на `http://localhost:8000`

### Шаг 4: Запустите ngrok

Откройте **новый** терминал (PowerShell или Command Prompt) и выполните:

**Вариант А** - если ngrok.exe в папке проекта:
```powershell
cd C:\wallet_project
.\ngrok.exe http 8000
```

**Вариант Б** - если ngrok.exe в другой папке (например, C:\ngrok):
```powershell
cd C:\ngrok
.\ngrok.exe http 8000
```

**Вариант В** - если добавили ngrok в PATH, просто:
```powershell
ngrok http 8000
```

### Шаг 5: Скопируйте HTTPS URL

После запуска ngrok вы увидите что-то вроде:
```
Forwarding   https://abc123.ngrok-free.app -> http://localhost:8000
```

Скопируйте HTTPS URL (например: `https://abc123.ngrok-free.app`)

**Важно**: Не закрывайте терминал с ngrok! Он должен оставаться открытым.

### Шаг 6: Готово!

Теперь ваш Django сервер доступен по HTTPS:
- Откройте в браузере: `https://abc123.ngrok-free.app`
- Манифест доступен: `https://abc123.ngrok-free.app/tonconnect-manifest.json`
- Tonkeeper сможет подключиться!

**Примечание**: При первом открытии ngrok может показать страницу с предупреждением - просто нажмите "Visit Site" или "Продолжить"

## Проверка манифеста

После запуска ngrok проверьте манифест:

### В браузере (самый простой способ):
Просто откройте: `https://ваш-ngrok-url.ngrok-free.app/tonconnect-manifest.json`

Должен вернуться JSON:
```json
{
  "url": "https://ваш-ngrok-url.ngrok-free.app",
  "name": "TON Wallet Test",
  "iconUrl": "https://ton.org/favicon.ico"
}
```

**Важно**: Замените `ваш-ngrok-url.ngrok-free.app` на реальный URL от ngrok!

## Альтернативный вариант: localtunnel (БЕЗ регистрации!)

Если не хотите регистрироваться в ngrok, используйте localtunnel - он проще:

### Шаг 1: Установите Node.js (если еще не установлен)

1. Скачайте Node.js: https://nodejs.org/ (LTS версия)
2. Установите (просто "Next" везде)
3. Перезапустите терминал

### Шаг 2: Установите localtunnel

Откройте PowerShell или Command Prompt:
```powershell
npm install -g localtunnel
```

**Если ошибка прав доступа** - запустите PowerShell от имени администратора (Win+X → "Терминал (Администратор)")

### Шаг 3: Запустите Django сервер

В первом терминале:
```powershell
cd C:\wallet_project\wallet
python manage.py runserver
```

### Шаг 4: Запустите localtunnel

Во втором терминале:
```powershell
lt --port 8000
```

Скопируйте HTTPS URL (например: `https://random-name.loca.lt`)

**Готово!** Используйте этот URL для Tonkeeper.

## Настройка для продакшена

В продакшене убедитесь, что:
1. Сервер доступен по HTTPS
2. Манифест доступен по пути `/tonconnect-manifest.json`
3. CORS заголовки правильно настроены
4. Иконка доступна по HTTPS

## Отладка

Если манифест все еще не загружается:

1. Проверьте консоль браузера на ошибки
2. Проверьте логи сервера Django
3. Убедитесь, что манифест доступен по правильному URL
4. Проверьте CORS заголовки в ответе сервера
5. Убедитесь, что используется HTTPS (не HTTP)

