from pytoniq import LiteClient
from pytoniq_core import Address
from .models import WalletSession, TransactionHistory, User
from django.utils import timezone
from datetime import datetime
import asyncio
import requests
import logging

logger = logging.getLogger(__name__)


def fetch_all_toncenter_transactions(address_str, limit_per_page=100, max_pages=20):
    """
    Загружаем максимально возможное количество транзакций через TON Center API
    постранично, двигаясь назад по истории с использованием lt/hash.
    """
    url = "https://toncenter.com/api/v2/getTransactions"
    all_txs = []
    params = {
        "address": address_str,
        "limit": limit_per_page,
    }

    for page in range(max_pages):
        try:
            response = requests.get(url, params=params, timeout=8)
            logger.info(f"TON Center API (page {page}) статус: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"TON Center API ошибка: {response.text[:300]}")
                break

            data = response.json()
            if not data.get("ok") or not data.get("result"):
                logger.warning(f"TON Center API вернул пустой результат или ok!=true: {data}")
                break

            result = data["result"]
            all_txs.extend(result)
            logger.info(f"TON Center API страница {page}, получено {len(result)} транзакций, всего {len(all_txs)}")

            # Если транзакций меньше лимита — дошли до конца
            if len(result) < limit_per_page:
                break

            # Готовим параметры для следующей страницы
            last_tx = result[-1]
            tx_id = last_tx.get("transaction_id") or last_tx.get("prev_transaction_id") or {}
            if isinstance(tx_id, dict):
                lt = tx_id.get("lt")
                h = tx_id.get("hash")
            else:
                lt = h = None

            if not lt or not h:
                logger.info("Нет lt/hash для продолжения пагинации, останавливаемся")
                break

            params["lt"] = lt
            params["hash"] = h
        except Exception as e:
            logger.error(f"Ошибка при пагинации TON Center API: {e}")
            break

    return all_txs


async def account_info(address_str):
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2, timeout=15)
    
    try:
        await client.connect()
        
        address = Address(address_str)
        account_state = await client.get_account_state(address)
        
        # Безопасная проверка активности аккаунта
        is_active = False
        if hasattr(account_state, 'state') and hasattr(account_state.state, 'type'):
            is_active = account_state.state.type == 'active'
        elif hasattr(account_state, 'state'):
            # Альтернативная проверка - если есть state, считаем активным
            is_active = account_state.state is not None
        
        # Безопасное получение last_transaction_lt
        last_transaction_lt = None
        if hasattr(account_state, 'last_transaction_lt'):
            last_transaction_lt = account_state.last_transaction_lt
        
        # Безопасное получение last_transaction_hash
        last_transaction_hash = None
        if hasattr(account_state, 'last_transaction_hash') and account_state.last_transaction_hash:
            if hasattr(account_state.last_transaction_hash, 'hex'):
                last_transaction_hash = account_state.last_transaction_hash.hex()
            else:
                last_transaction_hash = str(account_state.last_transaction_hash)
        
        result = {
            'address': address_str,
            'balance': account_state.balance / 1e9 if hasattr(account_state, 'balance') else 0,
            'is_active': is_active,
            'last_transaction_lt': last_transaction_lt,
            'last_transaction_hash': last_transaction_hash,
        }
        
        return result
    except Exception as e:
        print(f"Ошибка при получении информации об аккаунте: {e}")
        return None
    finally:
        await client.close()


async def get_balance(address_str, interval=60):
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2, timeout=15)
    
    try:
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
    except Exception as e:
        print(f"Ошибка подключения: {e}")
    finally:
        await client.close()



async def get_history_transaction(address_str):
    # Уменьшаем таймаут для более быстрого ответа
    client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2, timeout=10)
    
    try:
        await client.connect()
        
        address = Address(address_str)
        
        # Используем обычный get_account_state (не raw)
        account_state = await client.get_account_state(address)
        print(f"Тип account_state: {type(account_state)}")
        print(f"Атрибуты: {[attr for attr in dir(account_state) if not attr.startswith('_')]}")
        
        transactions = []
        current_lt = None
        current_hash = None
        
        # Пробуем получить last_transaction_lt из разных мест
        if hasattr(account_state, 'last_transaction_lt'):
            current_lt = account_state.last_transaction_lt
            print(f"Найден last_transaction_lt: {current_lt}")
        elif hasattr(account_state, 'account') and hasattr(account_state.account, 'last_transaction_lt'):
            current_lt = account_state.account.last_transaction_lt
            print(f"Найден last_transaction_lt через account: {current_lt}")
        elif hasattr(account_state, 'state') and hasattr(account_state.state, 'last_transaction_lt'):
            current_lt = account_state.state.last_transaction_lt
            print(f"Найден last_transaction_lt через state: {current_lt}")
        
        # Получаем hash
        if hasattr(account_state, 'last_transaction_hash'):
            current_hash = account_state.last_transaction_hash
        elif hasattr(account_state, 'account') and hasattr(account_state.account, 'last_transaction_hash'):
            current_hash = account_state.account.last_transaction_hash
        elif hasattr(account_state, 'state') and hasattr(account_state.state, 'last_transaction_hash'):
            current_hash = account_state.state.last_transaction_hash
        
        print(f"Получение транзакций для {address_str}, LT: {current_lt}, Hash: {current_hash}")

        # Если нет LT, используем внешние API. Сначала пытаемся tonapi.io,
        # затем постранично выкачиваем историю через TON Center API, чтобы получить
        # как можно больше транзакций (практически всю историю кошелька).
        if not current_lt:
            print("Нет last_transaction_lt, используем внешние API для получения транзакций...")
            try:
                # 1. Пытаемся забрать историю через TON API (tonapi.io)
                address_obj = Address(address_str)
                address_b64 = address_obj.to_str(is_bounceable=False)
                print(f"Используем адрес в формате base64: {address_b64}")

                url = f"https://tonapi.io/v2/accounts/{address_b64}/transactions"
                params = {
                    "limit": 400  # максимум, который нам позволит TON API
                }
                headers = {"Accept": "application/json"}
                response = requests.get(url, params=params, headers=headers, timeout=8)
                print(f"TON API статус: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    if data.get("transactions"):
                        transactions_data = data["transactions"]
                        print(f"Получено {len(transactions_data)} транзакций через TON API")
                        await client.close()
                        return transactions_data
                    else:
                        print(f"TON API вернул пустой результат: {list(data.keys())}")

                # 2. Если TON API не дал данных — используем постраничную загрузку TON Center
                print("Пробуем постранично загрузить историю через TON Center API")
                transactions_data = fetch_all_toncenter_transactions(
                    address_str,
                    limit_per_page=100,
                    max_pages=20,
                )
                print(f"TON Center (пагинация) вернул {len(transactions_data)} транзакций")
                await client.close()
                return transactions_data

            except Exception as e:
                print(f"Альтернативный API не сработал: {e}")
                import traceback
                traceback.print_exc()

            print("Не удалось получить транзакции, возвращаем пустой список")
            await client.close()
            return []

        # Преобразуем hash в правильный формат, если нужно
        if current_hash and not isinstance(current_hash, bytes):
            if hasattr(current_hash, 'hex'):
                # Если это объект с методом hex, конвертируем в bytes
                try:
                    current_hash = bytes.fromhex(current_hash.hex())
                except:
                    pass
            elif isinstance(current_hash, str) and len(current_hash) == 64:
                # Если это hex строка, конвертируем в bytes
                try:
                    current_hash = bytes.fromhex(current_hash)
                except:
                    pass
        
        max_iterations = 5  # Уменьшаем количество итераций для ускорения
        iteration = 0

        while current_lt and iteration < max_iterations:
            try:
                # Используем правильный метод для получения транзакций
                # Пробуем разные варианты методов
                txs = None
                
                # Вариант 1: raw_get_account_transactions
                if hasattr(client, 'raw_get_account_transactions'):
                    try:
                        if current_hash:
                            txs = await client.raw_get_account_transactions(
                                address=address,
                                lt=current_lt,
                                hash=current_hash,
                                limit=20  # Увеличиваем лимит за раз для уменьшения итераций
                            )
                        else:
                            txs = await client.raw_get_account_transactions(
                                address=address,
                                lt=current_lt,
                                limit=20  # Увеличиваем лимит за раз для уменьшения итераций
                            )
                    except Exception as e:
                        print(f"raw_get_account_transactions не сработал: {e}")
                
                # Вариант 2: get_transactions (если есть)
                if not txs and hasattr(client, 'get_transactions'):
                    try:
                        txs = await client.get_transactions(
                            address=address,
                            lt=current_lt,
                            hash=current_hash,
                            limit=10
                        )
                    except Exception as e:
                        print(f"get_transactions не сработал: {e}")
                
                # Вариант 3: raw_get_transactions
                if not txs and hasattr(client, 'raw_get_transactions'):
                    try:
                        txs = await client.raw_get_transactions(
                            address=address,
                            lt=current_lt,
                            hash=current_hash,
                            limit=10
                        )
                    except Exception as e:
                        print(f"raw_get_transactions не сработал: {e}")
                
                if not txs:
                    print(f"Не удалось получить транзакции на итерации {iteration}")
                    break

                if not txs:
                    print(f"Нет транзакций на итерации {iteration}")
                    break
                
                print(f"Получено {len(txs)} транзакций на итерации {iteration}")
                transactions.extend(txs)

                # Получаем следующую транзакцию для продолжения
                if txs:
                    last_tx = txs[-1]
                    current_lt = getattr(last_tx, 'prev_trans_lt', None)
                    current_hash = getattr(last_tx, 'prev_trans_hash', None)
                    
                    if not current_lt:
                        print("Достигнут конец истории транзакций")
                        break
                else:
                    break
                
                iteration += 1
                    
            except Exception as e:
                print(f"Ошибка при получении транзакций: {e}")
                import traceback
                traceback.print_exc()
                break
        
        print(f"Всего получено транзакций: {len(transactions)}")
        await client.close()
        return transactions
        
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        import traceback
        traceback.print_exc()
        await client.close()
        return []


def save_wallet_to_db(user, wallet_address, wallet_type=None):
    try:
        user.connect_wallet(wallet_address, wallet_type or 'TON')
        return True
    except Exception as e:
        print(f"Ошибка при сохранении кошелька: {e}")
        return False


def save_transactions_to_db(wallet_address, transactions):
    saved_count = 0
    print(f"Сохранение {len(transactions)} транзакций для {wallet_address}")
    
    for idx, tx in enumerate(transactions):
        try:
            # Проверяем тип транзакции - может быть dict (от API) или объект (от pytoniq)
            is_dict = isinstance(tx, dict)
            
            # Получаем hash транзакции
            tx_hash = None
            if is_dict:
                # Данные от TON API или TON Center API
                # TON API формат
                if 'hash' in tx:
                    tx_hash = tx['hash']
                # TON Center API формат
                elif 'transaction_id' in tx:
                    tx_id = tx['transaction_id']
                    if isinstance(tx_id, dict):
                        tx_hash = tx_id.get('hash', '')
                    else:
                        tx_hash = str(tx_id)
                elif 'tx_hash' in tx:
                    tx_hash = tx['tx_hash']
            elif hasattr(tx, 'hash'):
                if hasattr(tx.hash, 'hex'):
                    tx_hash = tx.hash.hex()
                else:
                    tx_hash = str(tx.hash)
            elif hasattr(tx, 'transaction_id'):
                tx_hash = str(tx.transaction_id)
            else:
                print(f"Транзакция {idx} не имеет hash, пропускаем")
                continue
            
            if not tx_hash:
                print(f"Транзакция {idx} имеет пустой hash, пропускаем")
                continue
                
            if TransactionHistory.objects.filter(tx_hash=tx_hash).exists():
                continue

            # Получаем timestamp (timezone-aware)
            timestamp = timezone.now()
            if is_dict:
                # Данные от TON API или TON Center API
                # TON API использует now или utime
                utime = tx.get('utime') or tx.get('now') or tx.get('timestamp', 0)
                if utime:
                    try:
                        # Если это строка с ISO форматом
                        if isinstance(utime, str):
                            # Пробуем распарсить ISO формат вручную
                            try:
                                # Формат: "2024-01-15T10:30:00Z" или "2024-01-15T10:30:00+00:00"
                                if 'T' in utime:
                                    utime_str = utime.replace('Z', '+00:00')
                                    naive_dt = datetime.strptime(utime_str.split('+')[0].split('.')[0], '%Y-%m-%dT%H:%M:%S')
                                    timestamp = timezone.make_aware(naive_dt)
                                else:
                                    naive_dt = datetime.fromtimestamp(int(utime))
                                    timestamp = timezone.make_aware(naive_dt)
                            except:
                                if utime.isdigit():
                                    naive_dt = datetime.fromtimestamp(int(utime))
                                    timestamp = timezone.make_aware(naive_dt)
                        else:
                            naive_dt = datetime.fromtimestamp(utime)
                            timestamp = timezone.make_aware(naive_dt)
                    except:
                        pass
            elif hasattr(tx, 'now'):
                try:
                    naive_dt = datetime.fromtimestamp(tx.now)
                    timestamp = timezone.make_aware(naive_dt)
                except:
                    pass
            elif hasattr(tx, 'utime'):
                try:
                    naive_dt = datetime.fromtimestamp(tx.utime)
                    timestamp = timezone.make_aware(naive_dt)
                except:
                    pass
            
            amount = 0
            from_address = ''
            to_address = wallet_address
            
            # Обрабатываем транзакции от TON API или TON Center API
            if is_dict:
                # TON API формат - может использовать actions
                if 'actions' in tx:
                    # TON API v2 формат с actions
                    for action in tx.get('actions', []):
                        if action.get('type') == 'TonTransfer':
                            transfer = action.get('TonTransfer', {})
                            if transfer:
                                value = transfer.get('amount', 0)
                                if value:
                                    amount = int(value) / 1e9
                                    from_address = action.get('sender', {}).get('address', '')
                                    to_address = action.get('recipient', {}).get('address', '')
                                    if to_address == wallet_address or from_address == wallet_address:
                                        break
                
                # Стандартный формат с in_msg/out_msgs
                if amount == 0 and ('in_msg' in tx or 'out_msgs' in tx):
                    in_msg = tx.get('in_msg')
                    out_msgs = tx.get('out_msgs', [])
                    
                    # Обрабатываем входящее сообщение
                    if in_msg:
                        msg_value = None
                        if isinstance(in_msg, dict):
                            msg_value = in_msg.get('value') or in_msg.get('amount')
                        else:
                            msg_value = getattr(in_msg, 'value', None) or getattr(in_msg, 'amount', None)
                        
                        if msg_value:
                            value = int(msg_value) if isinstance(msg_value, (int, str)) else 0
                            if value > 0:
                                amount = value / 1e9
                                if isinstance(in_msg, dict):
                                    from_address = in_msg.get('source', {}).get('address', '') if isinstance(in_msg.get('source'), dict) else in_msg.get('source', '')
                                else:
                                    from_address = str(getattr(in_msg, 'source', ''))
                                to_address = wallet_address
                    
                    # Обрабатываем исходящие сообщения, если не нашли входящие
                    if amount == 0 and out_msgs:
                        for msg in out_msgs if isinstance(out_msgs, list) else [out_msgs]:
                            msg_value = None
                            if isinstance(msg, dict):
                                msg_value = msg.get('value') or msg.get('amount')
                            else:
                                msg_value = getattr(msg, 'value', None) or getattr(msg, 'amount', None)
                            
                            if msg_value:
                                value = int(msg_value) if isinstance(msg_value, (int, str)) else 0
                                if value > 0:
                                    amount = value / 1e9
                                    from_address = wallet_address
                                    if isinstance(msg, dict):
                                        to_address = msg.get('destination', {}).get('address', '') if isinstance(msg.get('destination'), dict) else msg.get('destination', '')
                                    else:
                                        to_address = str(getattr(msg, 'destination', ''))
                                    break
            # Обрабатываем транзакции от pytoniq
            elif hasattr(tx, 'in_msg') and tx.in_msg:
                for msg in tx.in_msg if isinstance(tx.in_msg, list) else [tx.in_msg]:
                    try:
                        # Проверяем тип сообщения
                        msg_type = getattr(msg, 'msg_type', None)
                        if not msg_type:
                            # Пытаемся определить тип по структуре
                            if hasattr(msg, 'info') and hasattr(msg.info, 'msg_type'):
                                msg_type = msg.info.msg_type
                        
                        if msg_type == 'internal' or (hasattr(msg, 'value') and msg.value > 0):
                            # Получаем адрес назначения
                            dst = None
                            if hasattr(msg, 'dst'):
                                dst = str(msg.dst)
                            elif hasattr(msg, 'info') and hasattr(msg.info, 'dest'):
                                dst = str(msg.info.dest)
                            
                            if dst and dst == wallet_address:
                                # Это входящая транзакция
                                value = getattr(msg, 'value', 0)
                                if hasattr(value, '__truediv__'):
                                    amount = value / 1e9
                                else:
                                    amount = value / 1e9 if value else 0
                                
                                src = None
                                if hasattr(msg, 'src'):
                                    src = str(msg.src)
                                elif hasattr(msg, 'info') and hasattr(msg.info, 'src'):
                                    src = str(msg.info.src)
                                
                                from_address = src or ''
                                to_address = wallet_address
                                break
                    except Exception as e:
                        print(f"Ошибка при обработке входящего сообщения: {e}")
                        continue
            
            # Обрабатываем исходящие сообщения, если не нашли входящие
            if amount == 0 and hasattr(tx, 'out_msgs') and tx.out_msgs:
                for msg in tx.out_msgs if isinstance(tx.out_msgs, list) else [tx.out_msgs]:
                    try:
                        msg_type = getattr(msg, 'msg_type', None)
                        if not msg_type and hasattr(msg, 'info') and hasattr(msg.info, 'msg_type'):
                            msg_type = msg.info.msg_type
                        
                        if msg_type == 'internal' or (hasattr(msg, 'value') and msg.value > 0):
                            src = None
                            if hasattr(msg, 'src'):
                                src = str(msg.src)
                            elif hasattr(msg, 'info') and hasattr(msg.info, 'src'):
                                src = str(msg.info.src)
                            
                            if src and src == wallet_address:
                                # Это исходящая транзакция
                                value = getattr(msg, 'value', 0)
                                if hasattr(value, '__truediv__'):
                                    amount = value / 1e9
                                else:
                                    amount = value / 1e9 if value else 0
                                
                                dst = None
                                if hasattr(msg, 'dst'):
                                    dst = str(msg.dst)
                                elif hasattr(msg, 'info') and hasattr(msg.info, 'dest'):
                                    dst = str(msg.info.dest)
                                
                                from_address = wallet_address
                                to_address = dst or ''
                                break
                    except Exception as e:
                        print(f"Ошибка при обработке исходящего сообщения: {e}")
                        continue
            
            # Сохраняем транзакцию, даже если amount = 0 (может быть другая операция)
            if amount > 0 or True:  # Сохраняем все транзакции для отладки
                TransactionHistory.objects.create(
                    wallet_address=wallet_address,
                    tx_hash=tx_hash,
                    timestamp=timestamp,
                    amount=amount,
                    from_address=from_address,
                    to_address=to_address,
                    status='completed'
                )
                saved_count += 1
                if amount > 0:
                    print(f"Сохранена транзакция {tx_hash[:16]}... amount={amount} TON")
                            
        except Exception as e:
            print(f"Ошибка при сохранении транзакции {idx}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"Сохранено транзакций: {saved_count} из {len(transactions)}")
    return saved_count



