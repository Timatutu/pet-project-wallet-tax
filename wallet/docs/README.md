# Документация проекта

Эта папка содержит дополнительную документацию проекта:

- `er_diagram.png` или `er_diagram.svg` - ER-диаграмма базы данных
- `postman_collection.json` - экспортированная коллекция Postman с API endpoints
- `screenshots/` - скриншоты интерфейса приложения

## Создание ER-диаграммы

Для создания ER-диаграммы можно использовать:
- [draw.io](https://app.diagrams.net/) - онлайн инструмент
- [dbdiagram.io](https://dbdiagram.io/) - специализированный инструмент для диаграмм БД

## Структура базы данных

### Таблицы:

1. **users** - Пользователи
   - id (PK)
   - email (unique)
   - password
   - wallet_id (FK -> wallet_sessions.id)
   - is_active
   - is_staff
   - date_joined

2. **wallet_sessions** - Сессии кошельков
   - id (PK)
   - session_key (unique)
   - wallet_address
   - wallet_type
   - connected
   - created_at
   - updated_at

3. **transaction_history** - История транзакций
   - id (PK)
   - wallet_address (indexed)
   - tx_hash (unique, indexed)
   - timestamp (indexed)
   - amount
   - from_address
   - to_address
   - status
   - created_at

