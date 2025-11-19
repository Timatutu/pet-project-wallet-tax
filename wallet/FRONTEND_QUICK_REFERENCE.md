# Быстрая шпаргалка для фронтендера

## 🚀 Быстрый старт

### Базовый URL
```
http://localhost:8000
```

### API Endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/register/` | Регистрация |
| POST | `/api/login/` | Вход |

---

## 📝 Примеры кода

### Регистрация (Fetch)
```javascript
const response = await fetch('http://localhost:8000/api/register/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123',
    password_confirm: 'password123'
  })
});
const data = await response.json();
```

### Вход (Fetch)
```javascript
const response = await fetch('http://localhost:8000/api/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123'
  })
});
const data = await response.json();
```

### Сохранение токенов
```javascript
localStorage.setItem('access_token', data.tokens.access);
localStorage.setItem('refresh_token', data.tokens.refresh);
```

### Использование токена
```javascript
headers: {
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
  'Content-Type': 'application/json'
}
```

---

## 📦 Структура ответа

### Успешная регистрация/вход
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

### Ошибка валидации
```json
{
  "email": ["Пользователь с таким email уже существует."],
  "password": ["Пароль должен содержать минимум 8 символов."]
}
```

---

## ⚠️ Коды статусов

- `200 OK` - Успешный вход
- `201 Created` - Успешная регистрация
- `400 Bad Request` - Ошибка валидации
- `401 Unauthorized` - Не авторизован
- `500 Internal Server Error` - Ошибка сервера

---

## 🔑 JWT Токены

- **Access Token**: 15 минут
- **Refresh Token**: 7 дней

Хранить в `localStorage`:
```javascript
localStorage.setItem('access_token', token);
localStorage.getItem('access_token');
```

---

## ✅ Валидация

- Email: обязательное, валидный формат
- Password: минимум 8 символов
- Password Confirm: должен совпадать с password

---

## 📚 Полная документация

См. `FRONTEND_DOCS.md` для подробной информации.

