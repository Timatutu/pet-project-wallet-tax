# Документация для фронтендера

## 📋 Содержание
1. [Общая информация](#общая-информация)
2. [API Endpoints](#api-endpoints)
3. [Аутентификация](#аутентификация)
4. [Структура данных](#структура-данных)
5. [Примеры запросов](#примеры-запросов)
6. [Обработка ошибок](#обработка-ошибок)
7. [Настройка проекта](#настройка-проекта)

---

## Общая информация

### Технологии бэкенда
- **Django 5.2.6** - основной фреймворк
- **Django REST Framework** - для API
- **JWT (JSON Web Tokens)** - для аутентификации
- **SQLite** - база данных (по умолчанию)

### Базовый URL
```
http://localhost:8000
```

### Формат данных
Все запросы и ответы используют **JSON** формат.

### Content-Type
```
Content-Type: application/json
```

---

## API Endpoints

### 1. Регистрация пользователя

**POST** `/api/register/`

Создает нового пользователя в системе.

#### Запрос
```json
{
  "email": "user@example.com",
  "password": "password123",
  "password_confirm": "password123"
}
```

#### Успешный ответ (201 Created)
```json
{
  "id": 1,
  "email": "user@example.com",
  "date_joined": "2024-01-15T10:30:00Z",
  "wallet": {
    "session_key": "user_1705312200",
    "wallet_address": null,
    "wallet_type": null,
    "connected": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "tokens": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

#### Ошибки (400 Bad Request)
```json
{
  "email": ["Пользователь с таким email уже существует."],
  "password": ["Пароль должен содержать минимум 8 символов."],
  "password_confirm": ["Пароли не совпадают"]
}
```

#### Валидация
- `email`: обязательное поле, должен быть валидным email
- `password`: минимум 8 символов
- `password_confirm`: должен совпадать с `password`

---

### 2. Вход в систему

**POST** `/api/login/`

Аутентифицирует пользователя и возвращает JWT токены.

#### Запрос
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

#### Успешный ответ (200 OK)
```json
{
  "id": 1,
  "email": "user@example.com",
  "date_joined": "2024-01-15T10:30:00Z",
  "wallet": {
    "session_key": "user_1705312200",
    "wallet_address": "EQD...",
    "wallet_type": "tonkeeper",
    "connected": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z"
  },
  "tokens": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

#### Ошибки (400 Bad Request)
```json
{
  "non_field_errors": ["Неверный email или пароль"]
}
```

---

## Аутентификация

### JWT Токены

После успешной регистрации или входа, бэкенд возвращает два токена:

- **Access Token** - действителен 15 минут
- **Refresh Token** - действителен 7 дней

### Хранение токенов

Рекомендуется хранить токены в `localStorage`:

```javascript
// Сохранение токенов
localStorage.setItem('access_token', tokens.access);
localStorage.setItem('refresh_token', tokens.refresh);

// Получение токенов
const accessToken = localStorage.getItem('access_token');
const refreshToken = localStorage.getItem('refresh_token');
```

### Использование токенов

Для защищенных запросов добавляйте токен в заголовок:

```javascript
headers: {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
}
```

### Структура токена

Access токен содержит:
```json
{
  "token_type": "access",
  "user_id": 1,
  "email": "user@example.com",
  "exp": 1705313100,
  "iat": 1705312200
}
```

Refresh токен содержит:
```json
{
  "token_type": "refresh",
  "user_id": 1,
  "exp": 1705917000,
  "iat": 1705312200
}
```

---

## Структура данных

### User (Пользователь)
```typescript
interface User {
  id: number;
  email: string;
  date_joined: string; // ISO 8601 format
  wallet: WalletSession;
}
```

### WalletSession (Сессия кошелька)
```typescript
interface WalletSession {
  session_key: string;
  wallet_address: string | null;
  wallet_type: string | null; // например: "tonkeeper", "tonhub"
  connected: boolean;
  created_at: string; // ISO 8601 format
  updated_at: string; // ISO 8601 format
}
```

### TransactionHistory (История транзакций)
```typescript
interface TransactionHistory {
  wallet_address: string;
  tx_hash: string;
  timestamp: string; // ISO 8601 format
  amount: number; // Decimal, 9 знаков после запятой
  from_address: string;
  to_address: string;
  status: 'completed' | 'pending' | 'failed';
  created_at: string; // ISO 8601 format
}
```

---

## Примеры запросов

### JavaScript (Fetch API)

#### Регистрация
```javascript
async function register(email, password, passwordConfirm) {
  try {
    const response = await fetch('http://localhost:8000/api/register/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: email,
        password: password,
        password_confirm: passwordConfirm
      })
    });

    const data = await response.json();

    if (response.ok) {
      // Сохраняем токены
      localStorage.setItem('access_token', data.tokens.access);
      localStorage.setItem('refresh_token', data.tokens.refresh);
      return { success: true, user: data };
    } else {
      return { success: false, errors: data };
    }
  } catch (error) {
    return { success: false, error: error.message };
  }
}
```

#### Вход
```javascript
async function login(email, password) {
  try {
    const response = await fetch('http://localhost:8000/api/login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: email,
        password: password
      })
    });

    const data = await response.json();

    if (response.ok) {
      // Сохраняем токены
      localStorage.setItem('access_token', data.tokens.access);
      localStorage.setItem('refresh_token', data.tokens.refresh);
      return { success: true, user: data };
    } else {
      return { success: false, errors: data };
    }
  } catch (error) {
    return { success: false, error: error.message };
  }
}
```

#### Защищенный запрос
```javascript
async function getProtectedData() {
  const accessToken = localStorage.getItem('access_token');
  
  if (!accessToken) {
    // Перенаправить на страницу входа
    window.location.href = '/login/';
    return;
  }

  try {
    const response = await fetch('http://localhost:8000/api/protected-endpoint/', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      }
    });

    if (response.status === 401) {
      // Токен истек, попробовать обновить
      const refreshed = await refreshToken();
      if (refreshed) {
        // Повторить запрос
        return getProtectedData();
      } else {
        // Перенаправить на страницу входа
        window.location.href = '/login/';
      }
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error:', error);
  }
}
```

### Axios

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/',
  headers: {
    'Content-Type': 'application/json',
  }
});

// Добавление токена к каждому запросу
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Регистрация
async function register(email, password, passwordConfirm) {
  try {
    const response = await api.post('/register/', {
      email,
      password,
      password_confirm: passwordConfirm
    });
    
    localStorage.setItem('access_token', response.data.tokens.access);
    localStorage.setItem('refresh_token', response.data.tokens.refresh);
    return { success: true, user: response.data };
  } catch (error) {
    return { 
      success: false, 
      errors: error.response?.data || { error: error.message }
    };
  }
}

// Вход
async function login(email, password) {
  try {
    const response = await api.post('/login/', {
      email,
      password
    });
    
    localStorage.setItem('access_token', response.data.tokens.access);
    localStorage.setItem('refresh_token', response.data.tokens.refresh);
    return { success: true, user: response.data };
  } catch (error) {
    return { 
      success: false, 
      errors: error.response?.data || { error: error.message }
    };
  }
}
```

---

## Обработка ошибок

### Типы ошибок

#### 400 Bad Request - Валидация
```json
{
  "email": ["Пользователь с таким email уже существует."],
  "password": ["Пароль должен содержать минимум 8 символов."]
}
```

#### 401 Unauthorized - Не авторизован
Токен отсутствует, истек или невалиден.

#### 500 Internal Server Error - Ошибка сервера
```json
{
  "error": "Internal server error",
  "detail": "Произошла ошибка при регистрации",
  "type": "ValueError"
}
```

### Функция обработки ошибок

```javascript
function handleApiError(error, response) {
  if (!response.ok) {
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      return response.json().then(data => {
        // Обработка ошибок валидации
        if (response.status === 400) {
          const errorMessages = [];
          
          Object.keys(data).forEach(key => {
            if (Array.isArray(data[key])) {
              errorMessages.push(...data[key]);
            } else {
              errorMessages.push(data[key]);
            }
          });
          
          return {
            success: false,
            errors: data,
            message: errorMessages.join(', ')
          };
        }
        
        // Обработка других ошибок
        return {
          success: false,
          error: data.error || data.detail || 'Произошла ошибка',
          errors: data
        };
      });
    } else {
      return {
        success: false,
        error: `HTTP ${response.status}: ${response.statusText}`
      };
    }
  }
  
  return { success: false, error: error.message };
}
```

### Локализованные сообщения об ошибках

Бэкенд возвращает ошибки на русском языке:

- **Email уже существует**: "Пользователь с таким email уже существует."
- **Короткий пароль**: "Пароль должен содержать минимум 8 символов."
- **Пароли не совпадают**: "Пароли не совпадают"
- **Неверные данные**: "Неверный email или пароль"
- **Обязательное поле**: "Email обязателен для заполнения."

---

## Настройка проекта

### Запуск бэкенда

```bash
# Активация виртуального окружения
# Windows
.venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Применение миграций
python manage.py migrate

# Создание суперпользователя (опционально)
python manage.py createsuperuser

# Запуск сервера
python manage.py runserver
```

Сервер будет доступен по адресу: `http://localhost:8000`

### CORS (если фронтенд на другом порту)

Если фронтенд запущен на другом порту (например, `http://localhost:3000`), нужно настроить CORS в `settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

### CSRF защита

Для AJAX запросов Django требует CSRF токен. Получить его можно:

```javascript
// Получение CSRF токена из cookies
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const csrftoken = getCookie('csrftoken');
```

**Примечание**: Для API endpoints (`/api/*`) CSRF защита отключена, токен не требуется.

---

## Полезные ссылки

- [Django REST Framework Documentation](https://www.django-rest-framework.org/)
- [JWT.io](https://jwt.io/) - для декодирования и проверки JWT токенов
- [MDN Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)

---

## Контакты

При возникновении вопросов обращайтесь к бэкенд-разработчику.

**Последнее обновление**: 2024-01-15

