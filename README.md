# TON Wallet Nalog — сервис расчёта налога по TON‑кошельку

Web‑приложение на Django, которое позволяет подключить TON‑кошелёк через TON Connect, загрузить историю транзакций и посчитать условный «налог» по исходящим операциям.  
Проект предназначен как учебный: демонстрирует работу с внешними блокчейн‑API, фоновую загрузку данных, расчёт агрегированной аналитики и защиту API через JWT.

---

## Features
- **Подключение TON‑кошелька** через TON Connect (например, Tonkeeper).
- **Отображение баланса** и статуса кошелька (активен / не активен).
- **Загрузка истории транзакций** с нескольких источников (pytoniq, TON API, TON Center API) с кэшированием в БД.
- **Фоновое обновление транзакций**: быстрый ответ из БД + параллельная догрузка новых данных из блокчейна.
- **Расчёт налога**:
  - только по **исходящим** транзакциям;
  - за **отдельный месяц**;
  - **помесячно за весь период**;
  - **итоговый налог** по всем месяцам.
- **JWT‑аутентификация** и автоматическое обновление access‑токена.
- **Документация для фронтенд‑разработчика** с описанием всех API.

---

## Tech Stack

- **Язык**: Python 3.10+
- **Фреймворк**: Django, Django REST Framework
- **База данных**: SQLite (по умолчанию Django; можно заменить на Postgres/MySQL)
- **Блокчейн / внешние сервисы**:
  - `pytoniq` (LiteClient для TON)
  - TON API (`tonapi.io`)
  - TON Center API (`toncenter.com`)
  - CoinGecko API (курс TON/USD)
- **Аутентификация**: JWT (через DRF + кастомная логика)
- **Фронтенд (текущая версия)**:
  - Django Templates (`wallet_nalog/templates/wallet_nalog/wallet_test.html`)
  - Чистый JavaScript (Fetch API, TonConnect UI)

Подробнее для фронтенда: см. `wallet/FRONTEND_DEV_GUIDE.md`.

---

## Installation

Инструкция приведена для локального запуска на Python 3.10+.

1. **Клонировать репозиторий**

```bash
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ>.git
cd wallet_project
```

2. **Создать и активировать виртуальное окружение**

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. **Установить зависимости**

```bash
cd wallet
pip install -r requirements.txt
```

4. **Выполнить миграции БД**

```bash
python manage.py migrate
```

5. **Создать суперпользователя (для доступа в Django admin)**

```bash
python manage.py createsuperuser
```

6. **Запустить сервер разработки**

```bash
python manage.py runserver 8001
```

Приложение будет доступно по адресу `http://localhost:8001/`.

7. **(Опционально) Настроить HTTPS‑доступ для Tonkeeper**

- Подробная инструкция в `wallet/TONCONNECT_SETUP.md` (ngrok / localtunnel).
- Полученный публичный HTTPS‑URL нужно прописать в `wallet/wallet_nalog/static/tonconnect-manifest.json`.

---

## Screenshots

Скриншоты рекомендуется положить в папку `docs/` и сослаться на них в README:

- **Главная страница приложения** (логин, подключение кошелька)

  ![](docs/screenshot_main.png)

- **Баланс и список транзакций**

  ![](docs/screenshot_transactions.png)

- **Блок расчёта налога помесячно**

  ![](docs/screenshot_tax_monthly.png)

- **Итоговый налог за период**

  ![](docs/screenshot_tax_total.png)

*(фактические файлы скриншотов нужно добавить самостоятельно)*  

---

## ER‑диаграмма базы данных

Основные сущности:

- **User** – пользователь Django.
- **WalletSession** – связь пользователя с конкретным TON‑кошельком.
- **TransactionHistory** – история транзакций для адреса кошелька.

Рекомендуется хранить схему в `docs/er_diagram.png` и добавить сюда:

![](docs/er_diagram.png)

Кратко:

- `User 1 — 1 WalletSession`
- `WalletSession 1 — N TransactionHistory`

---

## API (если в проекте есть API)

В проекте реализован REST API (Django REST Framework). Ниже краткий список основных эндпоинтов:

- **Аутентификация**
  - `POST /api/registration/` – регистрация пользователя (возвращает JWT‑токены).
  - `POST /api/login/` – логин (возвращает `access` и `refresh`).
  - `POST /api/refresh/` – обновление access‑токена по refresh‑токену.

- **Кошелёк**
  - `GET /api/Wallet/` – получить данные о текущем подключенном кошельке.
  - `PATCH /api/Wallet/` – сохранить/обновить адрес кошелька пользователя.

- **Баланс и транзакции**
  - `GET /api/wallet/balance/` – получить баланс кошелька (TON).
  - `GET /api/wallet/transactions/` – получить последние транзакции из БД (и запустить фоновое обновление).
    - Параметр `refresh=true` – принудительно обновить историю из блокчейна.

- **Налог**
  - `GET /api/tax/month/?year=YYYY&month=MM` – налог за указанный месяц.
  - `GET /api/tax/all/?start_year=YYYY&start_month=MM` – помесячный налог за период.
  - `GET /api/tax/total/?start_year=YYYY&start_month=MM` – итоговый налог и агрегированная статистика.

Полное описание форматов запросов/ответов: `wallet/FRONTEND_DEV_GUIDE.md`.

---

## Архитектурная схема

Простая блок‑схема взаимодействия компонентов может выглядеть так:

1. **Браузер / фронтенд**
   - Отправляет запросы к `/api/...` (Fetch / Axios).
   - Инициализирует TonConnect и соединяется с Tonkeeper.
2. **Backend (Django + DRF)**
   - Обрабатывает HTTP‑запросы, проверяет JWT.
   - Вызывает сервисы для работы с TON (`tonservice.py`).
   - Вызывает функции расчёта налога (`tax_calculator.py`).
3. **База данных (SQLite)**  
   - Хранит пользователей, сессии кошельков и историю транзакций.
4. **Внешние API**
   - TON blockchain (через `pytoniq`, TON API, TON Center API).
   - CoinGecko (курс TON/USD).

Рекомендуется оформить блок‑схему и сохранить как `docs/architecture.png`:

![](docs/architecture.png)

---

## Докстринги и внутренняя документация

В ключевых классах и функциях проекта используются (или должны использоваться) **docstring‑комментарии** на Python:

- сервисные функции в `wallet/wallet_nalog/tonservice.py` (работа с TON и транзакциями);
- функции расчёта налога в `wallet/wallet_nalog/tax_calculator.py`;
- основные view в `wallet/wallet_nalog/views.py`.

Рекомендуется при доработке проекта:

- добавлять docstring к каждому публичному классу/функции;
- кратко описывать:
  - назначение;
  - входные параметры;
  - возвращаемое значение;
  - возможные исключения / ошибки.

Это упростит сопровождение и защиту проекта на практике.

---

## Где почитать подробнее

- **Общая документация проекта**: `wallet/README.md` (детали по backend‑логике и расчёту налога).
- **Гайд для фронтендера**: `wallet/FRONTEND_DEV_GUIDE.md` (структура API, форматы данных, рекомендации по переписыванию фронта).
- **Настройка TON Connect и HTTPS‑доступа**: `wallet/TONCONNECT_SETUP.md`.

Этот README создан по требованиям учебной практики, чтобы любой разработчик мог быстро разобраться в проекте и запустить его локально. 


