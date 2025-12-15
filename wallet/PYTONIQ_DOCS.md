# Документация по библиотеке pytoniq

## 📋 Содержание
1. [Обзор](#обзор)
2. [Установка](#установка)
3. [Основные компоненты](#основные-компоненты)
4. [Базовое использование](#базовое-использование)
5. [Работа с аккаунтами](#работа-с-аккаунтами)
6. [Работа с транзакциями](#работа-с-транзакциями)
7. [Сканирование блоков](#сканирование-блоков)
8. [ADNL протокол](#adnl-протокол)
9. [Примеры использования](#примеры-использования)
10. [Полезные ресурсы](#полезные-ресурсы)

---

## Обзор

**pytoniq** — это Python SDK для работы с блокчейном TON (The Open Network). Библиотека предоставляет инструменты для взаимодействия с сетью TON через lite-серверы и ADNL протокол.

### Основные возможности:
- ✅ Подключение к TON блокчейну через LiteClient
- ✅ Получение информации об аккаунтах и балансах
- ✅ Работа с транзакциями
- ✅ Сканирование блоков
- ✅ Использование ADNL протокола
- ✅ Поддержка mainnet и testnet

### Связанные библиотеки:
- **pytoniq-core** — базовая библиотека с низкоуровневыми функциями
- **pytoniq** — высокоуровневая обёртка с удобным API

---

## Установка

### Установка pytoniq
```bash
pip install pytoniq
```

### Установка pytoniq-core (если нужна напрямую)
```bash
pip install pytoniq-core
```

### Установка конкретной версии
```bash
pip install pytoniq-core==0.1.45
```

---

## Основные компоненты

### 1. LiteClient
Клиент для взаимодействия с блокчейном TON через lite-серверы. Позволяет:
- Получать информацию о блоках
- Читать данные аккаунтов
- Отслеживать транзакции
- Получать состояние мастерчейна

### 2. ADNL (Abstract Datagram Network Layer)
Асинхронный протокол передачи данных в сети TON. Используется для:
- Прямого обмена данными между узлами
- Высокоскоростной передачи данных
- P2P коммуникации

### 3. BlockScanner
Утилита для сканирования блоков и отслеживания транзакций в реальном времени.

---

## Базовое использование

### Инициализация клиента

#### Подключение к mainnet
```python
from pytoniq import LiteClient
import asyncio

async def main():
    # Создание клиента с использованием конфигурации mainnet
    client = LiteClient.from_mainnet_config(
        ls_i=0,          # Индекс lite-сервера (0-15)
        trust_level=2,   # Уровень доверия (0-2)
        timeout=15       # Таймаут соединения в секундах
    )
    
    # Подключение к сети
    await client.connect()
    
    # Получение информации о мастерчейне
    masterchain_info = await client.get_masterchain_info()
    print(f"Последний блок: {masterchain_info.last}")
    print(f"Время: {masterchain_info.gen_utime}")
    
    # Закрытие соединения
    await client.close()

asyncio.run(main())
```

#### Подключение к testnet
```python
client = LiteClient.from_testnet_config(
    ls_i=0,
    trust_level=2,
    timeout=15
)
```

#### Ручная настройка клиента
```python
from pytoniq import LiteClient

client = LiteClient(
    host='127.0.0.1',
    port=17728,
    pub_key_hex='...',  # Публичный ключ lite-сервера
    timeout=15
)
```

---

## Работа с аккаунтами

### Получение информации об аккаунте
```python
from pytoniq import LiteClient
from pytoniq_core import Address

async def get_account_info():
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    # Адрес кошелька
    address = Address('EQD...')  # или Address('0:...')
    
    # Получение состояния аккаунта
    account_state = await client.get_account_state(address)
    
    if account_state.state.type == 'active':
        print(f"Баланс: {account_state.balance}")
        print(f"Последняя транзакция: {account_state.last_transaction_lt}")
        print(f"Последний блок: {account_state.last_transaction_hash}")
    else:
        print("Аккаунт не активен")
    
    await client.close()

asyncio.run(get_account_info())
```

### Получение баланса
```python
async def get_balance(address_str: str):
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    address = Address(address_str)
    account_state = await client.get_account_state(address)
    
    balance = account_state.balance  # в nanotons
    balance_tons = balance / 1e9  # конвертация в TON
    
    print(f"Баланс: {balance_tons} TON")
    
    await client.close()
    return balance_tons
```

### Проверка активности аккаунта
```python
async def is_account_active(address_str: str) -> bool:
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    address = Address(address_str)
    account_state = await client.get_account_state(address)
    
    is_active = account_state.state.type == 'active'
    
    await client.close()
    return is_active
```

---

## Работа с транзакциями

### Получение транзакций аккаунта
```python
from pytoniq_core import Address

async def get_account_transactions(address_str: str, limit: int = 10):
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    address = Address(address_str)
    account_state = await client.get_account_state(address)
    
    # Получение последних транзакций
    transactions = await client.get_account_transactions(
        address=address,
        lt=account_state.last_transaction_lt,
        hash=account_state.last_transaction_hash,
        limit=limit
    )
    
    for tx in transactions:
        print(f"LT: {tx.lt}")
        print(f"Hash: {tx.hash.hex()}")
        print(f"Время: {tx.now}")
        print(f"Входящие сообщения: {len(tx.in_msg)}")
        print(f"Исходящие сообщения: {len(tx.out_msgs)}")
        print("---")
    
    await client.close()
    return transactions
```

### Получение транзакций блока
```python
from pytoniq_core import BlockIdExt

async def get_block_transactions(block_id: BlockIdExt):
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    # Получение транзакций блока
    transactions = await client.raw_get_block_transactions_ext(block_id)
    
    for tx in transactions:
        print(f"Транзакция: {tx}")
        if tx.in_msg:
            print(f"Входящее сообщение: {tx.in_msg}")
    
    await client.close()
    return transactions
```

### Анализ транзакции
```python
async def analyze_transaction(tx_hash: str):
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    # Получение транзакции по хешу
    # (требует знания блока, где находится транзакция)
    
    # Пример анализа входящих сообщений
    # for msg in transaction.in_msg:
    #     if msg.msg_type == 'internal':
    #         print(f"От: {msg.src}")
    #         print(f"Кому: {msg.dst}")
    #         print(f"Сумма: {msg.value}")
    #         print(f"Тело: {msg.body}")
    
    await client.close()
```

---

## Сканирование блоков

### Базовое сканирование
```python
from pytoniq import LiteClient, BlockScanner
from pytoniq_core import BlockIdExt

async def handle_block(block: BlockIdExt):
    """Обработчик блока"""
    if block.workchain == -1:  # Пропускаем мастерчейн блоки
        return
    
    print(f"Блок: {block}")
    print(f"Workchain: {block.workchain}")
    print(f"Shard: {block.shard}")
    print(f"Seqno: {block.seqno}")
    
    # Получение транзакций блока
    transactions = await client.raw_get_block_transactions_ext(block)
    
    for tx in transactions:
        print(f"  Транзакция: {tx}")
        if tx.in_msg:
            print(f"    Входящее сообщение: {tx.in_msg}")

async def main():
    global client
    client = LiteClient.from_mainnet_config(ls_i=14, trust_level=0, timeout=20)
    await client.connect()
    
    # Создание сканера блоков
    scanner = BlockScanner(
        client=client,
        block_handler=handle_block
    )
    
    # Запуск сканирования
    await scanner.run()
    
    await client.close()

asyncio.run(main())
```

### Сканирование с фильтрацией
```python
async def handle_block_filtered(block: BlockIdExt):
    """Обработчик с фильтрацией по адресу"""
    target_address = Address('EQD...')
    
    transactions = await client.raw_get_block_transactions_ext(block)
    
    for tx in transactions:
        # Проверка входящих сообщений
        if tx.in_msg:
            for msg in tx.in_msg:
                if msg.msg_type == 'internal' and msg.dst == target_address:
                    print(f"Найдена транзакция на адрес {target_address}")
                    print(f"От: {msg.src}")
                    print(f"Сумма: {msg.value}")
        
        # Проверка исходящих сообщений
        if tx.out_msgs:
            for msg in tx.out_msgs:
                if msg.msg_type == 'internal' and msg.src == target_address:
                    print(f"Найдена транзакция с адреса {target_address}")
                    print(f"Кому: {msg.dst}")
                    print(f"Сумма: {msg.value}")

async def scan_for_address(address_str: str):
    client = LiteClient.from_mainnet_config(ls_i=14, trust_level=0, timeout=20)
    await client.connect()
    
    scanner = BlockScanner(
        client=client,
        block_handler=handle_block_filtered
    )
    
    await scanner.run()
    await client.close()
```

---

## ADNL протокол

### Базовое использование ADNL
```python
from pytoniq import AdnlClient

async def adnl_example():
    # Создание ADNL клиента
    client = AdnlClient(
        host='127.0.0.1',
        port=30300
    )
    
    await client.connect()
    
    # Отправка запроса через ADNL
    # (пример зависит от конкретного использования)
    
    await client.close()
```

---

## Примеры использования

### Пример 1: Мониторинг баланса кошелька
```python
import asyncio
from pytoniq import LiteClient
from pytoniq_core import Address

async def monitor_balance(address_str: str, interval: int = 60):
    """Мониторинг баланса кошелька с заданным интервалом"""
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    address = Address(address_str)
    last_balance = None
    
    while True:
        try:
            account_state = await client.get_account_state(address)
            current_balance = account_state.balance / 1e9  # в TON
            
            if last_balance is not None and current_balance != last_balance:
                diff = current_balance - last_balance
                print(f"Баланс изменился: {last_balance} -> {current_balance} TON ({diff:+.9f})")
            
            last_balance = current_balance
            print(f"Текущий баланс: {current_balance} TON")
            
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"Ошибка: {e}")
            await asyncio.sleep(interval)
    
    await client.close()

# Запуск мониторинга
# asyncio.run(monitor_balance('EQD...', interval=60))
```

### Пример 2: Получение истории транзакций
```python
async def get_transaction_history(address_str: str, limit: int = 50):
    """Получение истории транзакций аккаунта"""
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    address = Address(address_str)
    account_state = await client.get_account_state(address)
    
    transactions = []
    current_lt = account_state.last_transaction_lt
    current_hash = account_state.last_transaction_hash
    
    while len(transactions) < limit and current_lt:
        try:
            txs = await client.get_account_transactions(
                address=address,
                lt=current_lt,
                hash=current_hash,
                limit=10
            )
            
            if not txs:
                break
            
            transactions.extend(txs)
            
            # Обновление для следующей итерации
            if txs:
                current_lt = txs[-1].prev_trans_lt
                current_hash = txs[-1].prev_trans_hash
            
        except Exception as e:
            print(f"Ошибка при получении транзакций: {e}")
            break
    
    await client.close()
    return transactions[:limit]
```

### Пример 3: Отслеживание новых транзакций
```python
async def track_new_transactions(address_str: str):
    """Отслеживание новых транзакций для адреса"""
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    address = Address(address_str)
    account_state = await client.get_account_state(address)
    last_lt = account_state.last_transaction_lt
    
    print(f"Отслеживание транзакций для {address_str}")
    print(f"Последняя транзакция LT: {last_lt}")
    
    while True:
        try:
            current_state = await client.get_account_state(address)
            current_lt = current_state.last_transaction_lt
            
            if current_lt > last_lt:
                print(f"Обнаружена новая транзакция! LT: {current_lt}")
                
                # Получение новых транзакций
                new_txs = await client.get_account_transactions(
                    address=address,
                    lt=current_lt,
                    hash=current_state.last_transaction_hash,
                    limit=10
                )
                
                for tx in new_txs:
                    if tx.lt > last_lt:
                        print(f"  Транзакция LT: {tx.lt}, Hash: {tx.hash.hex()}")
                
                last_lt = current_lt
            
            await asyncio.sleep(5)  # Проверка каждые 5 секунд
            
        except Exception as e:
            print(f"Ошибка: {e}")
            await asyncio.sleep(5)
    
    await client.close()
```

### Пример 4: Получение информации о блоке
```python
async def get_block_info(workchain: int, shard: int, seqno: int):
    """Получение информации о конкретном блоке"""
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    # Получение информации о мастерчейне
    masterchain_info = await client.get_masterchain_info()
    
    # Создание BlockIdExt для нужного блока
    from pytoniq_core import BlockIdExt, ShardIdent, BlockId
    
    block_id = BlockIdExt(
        workchain=workchain,
        shard=shard,
        seqno=seqno,
        root_hash=b'...',  # root_hash блока
        file_hash=b'...'   # file_hash блока
    )
    
    # Получение блока
    block = await client.raw_get_block(block_id)
    
    print(f"Блок: {block_id}")
    print(f"Время: {block.info.gen_utime}")
    print(f"Транзакций: {len(block.transactions)}")
    
    await client.close()
    return block
```

---

## Обработка ошибок

### Базовая обработка ошибок
```python
from pytoniq import LiteClient
from pytoniq_core import Address

async def safe_get_account(address_str: str):
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    
    try:
        await client.connect()
        address = Address(address_str)
        account_state = await client.get_account_state(address)
        return account_state
    except ConnectionError as e:
        print(f"Ошибка подключения: {e}")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return None
    finally:
        await client.close()
```

### Retry механизм
```python
import asyncio
from pytoniq import LiteClient

async def get_with_retry(client_func, max_retries=3, delay=1):
    """Выполнение функции с повторными попытками"""
    for attempt in range(max_retries):
        try:
            return await client_func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"Попытка {attempt + 1} не удалась: {e}. Повтор через {delay} сек...")
            await asyncio.sleep(delay)
            delay *= 2  # Экспоненциальная задержка

async def example_with_retry():
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
    await client.connect()
    
    try:
        result = await get_with_retry(
            lambda: client.get_masterchain_info(),
            max_retries=3
        )
        print(result)
    finally:
        await client.close()
```

---

## Полезные ресурсы

### Официальные ресурсы
- **GitHub репозиторий pytoniq**: https://github.com/yungwine/pytoniq
- **GitHub репозиторий pytoniq-core**: https://github.com/yungwine/pytoniq-core
- **PyPI pytoniq**: https://pypi.org/project/pytoniq/
- **PyPI pytoniq-core**: https://pypi.org/project/pytoniq-core/

### Документация TON
- **TON Documentation**: https://docs.ton.org/
- **TON Whitepaper**: https://ton.org/docs/

### Полезные инструменты
- **TON Explorer**: https://tonscan.org/
- **TON Testnet Explorer**: https://testnet.tonscan.org/
- **TON Center API**: https://toncenter.com/api/v2/

### Примеры кода
- Примеры из репозитория pytoniq на GitHub
- TON SDK примеры: https://github.com/ton-blockchain/ton

---

## Часто задаваемые вопросы

### Q: Как конвертировать баланс из nanotons в TON?
**A:** Разделите на 1e9:
```python
balance_tons = balance_nanotons / 1e9
```

### Q: Как получить адрес в разных форматах?
**A:** Используйте класс Address:
```python
from pytoniq_core import Address

address = Address('EQD...')  # User-friendly формат
print(address.to_str(is_user_friendly=True))   # EQD...
print(address.to_str(is_user_friendly=False)) # 0:...
print(address.to_str(is_bounceable=False))     # UQD...
```

### Q: Как выбрать правильный lite-сервер?
**A:** Используйте индекс от 0 до 15. Рекомендуется использовать несколько серверов для надежности.

### Q: В чем разница между pytoniq и pytoniq-core?
**A:** 
- `pytoniq-core` — низкоуровневая библиотека с базовыми функциями
- `pytoniq` — высокоуровневая обёртка с удобным API и дополнительными возможностями

### Q: Как обрабатывать большие объемы транзакций?
**A:** Используйте пагинацию и обрабатывайте транзакции батчами:
```python
limit = 100
offset = 0
while True:
    txs = await get_transactions(limit=limit, offset=offset)
    if not txs:
        break
    process_transactions(txs)
    offset += limit
```

---

## Заключение

Библиотека `pytoniq` предоставляет мощный инструментарий для работы с блокчейном TON. Основные преимущества:

- ✅ Простой и понятный API
- ✅ Асинхронная работа
- ✅ Поддержка mainnet и testnet
- ✅ Работа с транзакциями и аккаунтами
- ✅ Сканирование блоков в реальном времени

Начните с простых примеров и постепенно изучайте более сложные возможности библиотеки.

**Последнее обновление**: 2024-01-15

