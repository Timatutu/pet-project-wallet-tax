## Проект TON Wallet Nalog – обзор и документация

Этот проект – Django‑приложение для:

- подключения TON‑кошелька через TON Connect;
- просмотра баланса и истории транзакций;
- расчёта «налога» (условной суммы к уплате) по исходящим транзакциям кошелька.

Проект разделён на:

- backend: Django + Django REST Framework, приложение `wallet_nalog`;
- простой HTML‑фронт (`wallet_nalog/templates/wallet_nalog/wallet_test.html`), который будет позже переписан фронтендером.

Ниже описана архитектура, основные модули и вся логика расчёта налога.

---

## Запуск проекта локально

### Зависимости

- Python 3.10+
- virtualenv (рекомендуется)
- Django, DRF, pytoniq и прочее – см. `requirements.txt`

### Шаги запуска

```bash
cd wallet
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver 8001
```

Проект будет доступен по адресу `http://localhost:8001/`.

---

## Подключение TON‑кошелька (TON Connect)

### Манифест

Файл: `wallet_nalog/static/tonconnect-manifest.json`

```json
{
    "url": "https://ВАШ_ПУБЛИЧНЫЙ_URL",
    "name": "TON Wallet Test",
    "iconUrl": "https://ВАШ_ПУБЛИЧНЫЙ_URL/static/wallet_nalog/icon.png"
}
```

- `url` – публичный HTTPS‑адрес, по которому фронт доступен с телефона (через ngrok или другой туннель).
- `iconUrl` – иконка dApp (можно оставить сторонний favicon, но лучше свой домен).

### Туннель (ngrok / localtunnel)

Подробная инструкция – в `TONCONNECT_SETUP.md`. Кратко:

- Django слушает `http://localhost:8001`.
- ngrok или localtunnel публикует этот адрес наружу как `https://...ngrok.io` или `https://....loca.lt`.
- Этот URL нужно прописать в `tonconnect-manifest.json` и использовать при подключении dApp в Tonkeeper.

### CSRF и безопасность

Так как API использует JWT‑аутентификацию, CSRF защита для API и манифеста отключена специально:

- кастомный middleware `wallet_nalog.middleware.DisableCSRFForAPI`:
  - отключает CSRF для всех путей, начинающихся с `/api/`;
  - отключает CSRF для `/tonconnect-manifest.json`.

---

## Архитектура backend‑приложения

Основное приложение: `wallet_nalog`.

### Модели (`wallet_nalog/models.py`)

- **User**
  - Пользователь Django, расширенный связью с `WalletSession`.
- **WalletSession**
  - `user` – владелец сессии.
  - `wallet_address` – TON‑адрес кошелька (формат `0:...`).
  - `wallet_type` – тип кошелька (по умолчанию `TON`).
  - `connected` – флаг, подключён ли кошелёк сейчас.
  - Взаимодействует с TON Connect – после успешного подключения в эту модель сохраняется адрес.
- **TransactionHistory**
  - `wallet_address` – адрес кошелька, к которому относится транзакция.
  - `tx_hash` – уникальный идентификатор транзакции (используется для дедупликации).
  - `timestamp` – время транзакции (timezone‑aware).
  - `amount` – сумма в TON (всегда положительная, знак направления задаётся `from_address`/`to_address`).
  - `from_address` – адрес отправителя.
  - `to_address` – адрес получателя.
  - `status` – статус (`completed` и т.п.).
  - `created_at` – время сохранения записи в БД.

Расчёт налога всегда идёт по записям `TransactionHistory`, где:

- `wallet_address = <адрес пользователя>`;
- `from_address = <адрес пользователя>` (то есть только исходящие транзакции).

### Аутентификация и JWT

- Пользователь логинится через `/api/login/`, получает `access` и `refresh` JWT‑токены.
- Фронтенд хранит их в `localStorage` и прикладывает `Authorization: Bearer <access>` ко всем запросам к `/api/...`.
- При истечении `access` фронт вызывает `/api/refresh/` и обновляет оба токена.
- Все защищённые view помечены `@permission_classes([IsAuthenticated])`.

### Основные view (`wallet_nalog/views.py`)

#### Управление кошельком

- `Registration`, `Login` – регистрация/логин, выдают JWT.
- `connect_wallet` / `Wallet` – сохранение и получение информации о текущем подключенном кошельке (`WalletSession`).

#### Баланс и транзакции

- `get_wallet_balance` (`/api/wallet/balance/`, GET)
  - Вытаскивает информацию об аккаунте через `account_info` из `tonservice.py`.
  - Возвращает: адрес, баланс в TON, флаг активности.

- `get_wallet_transactions` (`/api/wallet/transactions/`, GET)
  - Требует авторизации.
  - Параметр `refresh=true` принудительно обновляет историю из блокчейна.
  - Логика:
    1. Если `refresh` **не указан**:
       - Берём до 50 последних записей из `TransactionHistory` для данного `wallet_address`.
       - Если они есть – сразу отдаём их на фронт (быстро).
       - Параллельно в отдельном потоке:
         - вызываем `get_history_transaction(wallet_address)` из `tonservice.py`;
         - сохраняем новые транзакции через `save_transactions_to_db`.
    2. Если в БД нет записей или `refresh=true`:
       - вызываем `get_history_transaction` синхронно;
       - сохраняем всё в БД;
       - снова читаем 50 последних из БД и отдаём их фронту.

#### Налог (`/api/tax/...`)

Все налоговые view используют функции из `wallet_nalog/tax_calculator.py`.

- `get_tax_for_month` (`/api/tax/month/`, GET)
  - Параметры: `year`, `month`.
  - Находит все исходящие транзакции (`from_address = wallet_address`) за указанный месяц и считает налог.
  - Возвращает структуру из `calculate_tax_for_month`.

- `get_tax_for_all_months` (`/api/tax/all/`, GET)
  - Параметры: `start_year`, `start_month` (опционально).
  - Определяет первый и последний месяцы по фактическим транзакциям в `TransactionHistory`.
  - Вызывает `calculate_tax_for_all_months`, возвращает список по месяцам + их количество.

- `get_total_tax` (`/api/tax/total/`, GET)
  - Параметры: `start_year`, `start_month` (опционально).
  - Вызывает `calculate_total_tax`:
    - суммарный налог;
    - суммарный объём исходящих переводов;
    - количество транзакций;
    - период (первый и последний месяц);
    - курс TON/USD, использованный для расчётов.

---

## Работа с TON – `wallet_nalog/tonservice.py`

Основные функции:

- `account_info(address_str)`
  - Через `pytoniq.LiteClient` получает состояние аккаунта:
    - баланс;
    - активность;
    - `last_transaction_lt` и `last_transaction_hash` (если есть).

- `get_history_transaction(address_str)`
  - Пытается получить историю транзакций максимально полно:
    1. Подключается к mainnet через `LiteClient`.
    2. Пытается достать `last_transaction_lt` и `last_transaction_hash`.
    3. Если `last_transaction_lt` **есть**:
       - использует методы `raw_get_account_transactions` / `get_transactions` / `raw_get_transactions`
         с пагинацией по `lt/hash` (ограничение по количеству итераций для скорости).
    4. Если `last_transaction_lt` **нет** (как в некоторых SimpleAccount):
       - пробует TON API (`tonapi.io/v2/accounts/{address_b64}/transactions`, `limit ~ 400`);
       - если TON API недоступен или возвращает пусто:
         - вызывает `fetch_all_toncenter_transactions(...)`.

- `fetch_all_toncenter_transactions(address_str, limit_per_page=100, max_pages=20)`
  - HTTP‑клиент к `https://toncenter.com/api/v2/getTransactions`.
  - Загружает транзакции постранично:
    - на каждой странице запрашивает `limit_per_page`;
    - извлекает из последней транзакции `transaction_id.lt` и `transaction_id.hash`;
    - подставляет их как `lt` и `hash` в следующий запрос (двигается назад во времени).
  - Останавливается, если:
    - страница вернула меньше `limit_per_page`;
    - нет `lt/hash` для продолжения;
    - достигнут лимит страниц `max_pages`;
    - произошла ошибка или rate‑limit (код 429).

- `save_transactions_to_db(wallet_address, transactions)`
  - Принимает список транзакций из TON API, TON Center API или `pytoniq`.
  - Для каждой транзакции:
    - вычисляет `tx_hash` (поддерживает разные форматы);
    - пропускает транзакции с пустым hash или уже существующие в БД;
    - аккуратно парсит `timestamp` (epoch, ISO‑строка и т.п.), всегда переводит в aware‑datetime;
    - вычисляет:
      - `amount` (в TON, positive);
      - `from_address` / `to_address` на основе `in_msg` / `out_msgs` / `actions`;
      - умеет различать входящие и исходящие сообщения для адреса `wallet_address`;
    - создаёт запись `TransactionHistory`.

Важно: для расчёта налога мы используем только те записи, где:

- `wallet_address` = адрес кошелька;
- `from_address` = тот же адрес (то есть исходящие переводы).

---

## Логика расчёта налога – `wallet_nalog/tax_calculator.py`

Основная идея: налог считается **по исходящим транзакциям**, суммируя объёмы отправленных средств.

### Параметры и ставки

- `TAX_THRESHOLD_USD = 5000` – порог в долларах.
- `TAX_RATE_LOW = 0.01` – ставка налога 1% для сумм **ниже** порога.
- `TAX_RATE_HIGH = 0.005` – ставка 0.5% для сумм **выше или равных** порогу.

Курс TON/USD берётся из API CoinGecko:

- `get_ton_price_usd()`:
  - запрашивает `https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd`;
  - при ошибке или таймауте возвращает фиксированный запасной курс `5.0` USD за 1 TON.

### Расчёт налога по одной транзакции

- `calculate_tax_for_transaction(amount_ton, ton_price_usd=None)`:
  - переводит `amount_ton` в Decimal;
  - считает сумму в долларах: `amount_usd = amount_ton * ton_price_usd`;
  - выбирает ставку:
    - если `amount_usd < 5000` → 1%;
    - иначе → 0.5%;
  - возвращает:
    - исходную сумму в TON и USD;
    - ставку;
    - сумму налога в TON и USD.

### Налог за месяц

- `calculate_tax_for_month(wallet_address, year, month, ton_price_usd=None)`:
  - строит интервал дат `[start_date, end_date)` по локальному `TIME_ZONE` (через `timezone.make_aware`).
  - выбирает из `TransactionHistory` все записи:
    - `wallet_address = wallet_address`;
    - `from_address = wallet_address`;
    - `timestamp` в заданном интервале;
    - сортирует по времени.
  - если исходящих транзакций нет – возвращает структуру с нулями.
  - для каждой транзакции:
    - берёт `amount`;
    - вызывает `calculate_tax_for_transaction`;
    - накапливает:
      - `total_sent_ton`, `total_sent_usd`;
      - `total_tax_ton`, `total_tax_usd`;
      - добавляет детализированную запись в `transactions` (hash, время, суммы, ставка, налог).
  - итоговая структура:
    - `year`, `month`;
    - `total_sent_ton`, `total_sent_usd`;
    - `total_tax_ton`, `total_tax_usd`;
    - `transactions_count`;
    - `transactions` – список по каждой исходящей транзакции.

### Налог по всем месяцам

- `calculate_tax_for_all_months(wallet_address, start_year=None, start_month=None, ton_price_usd=None)`:
  - находит первую и последнюю исходящие транзакции пользователя;
  - определяет период по годам/месяцам;
  - опционально позволяет задать `start_year` и `start_month` вручную;
  - для каждого месяца в диапазоне вызывает `calculate_tax_for_month` и **всегда добавляет** результат в список (в т.ч. месяцы с нулевым налогом).

### Итоговый налог

- `calculate_total_tax(wallet_address, start_year=None, start_month=None, ton_price_usd=None)`:
  - вызывает `calculate_tax_for_all_months`;
  - суммирует:
    - `total_tax_ton`, `total_tax_usd`;
    - `total_sent_ton`, `total_sent_usd`;
    - общее количество транзакций;
  - определяет период (`start` и `end` в формате `YYYY-MM`);
  - возвращает:
    - общие суммы и налог;
    - используемый курс TON/USD;
    - список помесячных результатов;
    - период.

---

## Документация для фронтенд‑разработчика

Подробная фронтенд‑документация вынесена в отдельный файл:

- `FRONTEND_DEV_GUIDE.md`

Там описаны:

- все REST‑эндпоинты `/api/...` с примерами запросов и ответов;
- структура данных по транзакциям и налогу;
- как работает аутентификация и обновление токена;
- текущая логика шаблона `wallet_test.html` и рекомендации по переписыванию фронта (на любой фреймворк).


