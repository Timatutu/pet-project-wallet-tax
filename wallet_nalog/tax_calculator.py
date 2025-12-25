from .tonservice import get_balance, get_history_transaction, account_info
from .models import TransactionHistory, WalletSession
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import asyncio
import requests


# Ставка налога: 5% от прибыли по каждой продаже
TAX_RATE_PROFIT = Decimal('0.05')


def get_ton_price_usd():
    """
    Текущая цена TON в USD для расчёта эквивалента.
    Если API недоступно, используем запасное значение.
    """
    try:
        response = requests.get(
            'https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd',
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            price = data.get('the-open-network', {}).get('usd')
            if price:
                return Decimal(str(price))
    except Exception as e:
        print(f"Ошибка при получении курса TON/USD: {e}")
    
    # Запасной курс, если API недоступно
    return Decimal('5.0') 


def calculate_tax_for_month(wallet_address, year, month, ton_price_usd=None):
    """
    Расчёт налога за месяц по логике:
    - считаем покупки и продажи TON;
    - для каждой продажи считаем прибыль = сумма продажи - сумма покупок (FIFO),
      использованных под эту продажу;
    - если прибыль > 0, налог = 5% от прибыли;
    - если продажа "в минус" (прибыль <= 0), налог не берётся.
    """
    # Используем timezone-aware даты, совместимые с Django
    start_naive = datetime(year, month, 1)
    if month == 12:
        end_naive = datetime(year + 1, 1, 1)
    else:
        end_naive = datetime(year, month + 1, 1)

    # Делаем aware в соответствии с настройками TIME_ZONE
    start_date = timezone.make_aware(start_naive)
    end_date = timezone.make_aware(end_naive)
    
    month_txs = TransactionHistory.objects.filter(
        wallet_address=wallet_address,
        timestamp__gte=start_date,
        timestamp__lt=end_date
    ).order_by('timestamp')
    
    if ton_price_usd is None:
        ton_price_usd = get_ton_price_usd()
    
    total_tax_ton = Decimal('0')
    total_tax_usd = Decimal('0')
    total_sent_ton = Decimal('0')   # суммарный объём продаж
    total_sent_usd = Decimal('0')
    transactions_detail = []

    # Пул покупок для FIFO-списания при продажах
    buys_pool = []  # элементы: {'amount': Decimal}

    for tx in month_txs:
        amount_ton = Decimal(str(tx.amount))

        # Определяем тип операции относительно нашего кошелька
        is_buy = tx.to_address == wallet_address and tx.from_address != wallet_address
        is_sell = tx.from_address == wallet_address and tx.to_address != wallet_address

        if not is_buy and not is_sell:
            # Внутренние переводы самому себе и прочее — пропускаем
            continue

        amount_usd = amount_ton * ton_price_usd

        if is_buy:
            # Покупка: просто добавляем в пул, налог не берём
            buys_pool.append({'amount': amount_ton})
            transactions_detail.append({
                'tx_hash': tx.tx_hash,
                'timestamp': tx.timestamp.isoformat(),
                'operation_type': 'buy',
                'amount_ton': float(amount_ton),
                'amount_usd': float(amount_usd),
                'matched_buy_amount_ton': float(amount_ton),
                'profit_ton': 0.0,
                'profit_usd': 0.0,
                'tax_rate': float(TAX_RATE_PROFIT),
                'tax_amount_ton': 0.0,
                'tax_amount_usd': 0.0,
            })
            continue

        # Продажа: считаем, какой объём покупок идёт "под неё" (FIFO)
        total_sent_ton += amount_ton
        total_sent_usd += amount_usd

        remaining = amount_ton
        matched_buy = Decimal('0')

        while remaining > 0 and buys_pool:
            lot = buys_pool[0]
            lot_amount = lot['amount']

            use_amount = remaining if remaining <= lot_amount else lot_amount
            matched_buy += use_amount
            remaining -= use_amount
            lot_amount -= use_amount

            if lot_amount <= 0:
                buys_pool.pop(0)
            else:
                lot['amount'] = lot_amount

        # Прибыль в TON = объём продажи - объём покупок, отнесённый на эту продажу
        profit_ton = amount_ton - matched_buy
        if profit_ton > 0:
            tax_ton = (profit_ton * TAX_RATE_PROFIT).quantize(Decimal('0.000000001'))
        else:
            profit_ton = Decimal('0')
            tax_ton = Decimal('0')

        profit_usd = profit_ton * ton_price_usd
        tax_usd = tax_ton * ton_price_usd

        total_tax_ton += tax_ton
        total_tax_usd += tax_usd

        transactions_detail.append({
            'tx_hash': tx.tx_hash,
            'timestamp': tx.timestamp.isoformat(),
            'operation_type': 'sell',
            'amount_ton': float(amount_ton),
            'amount_usd': float(amount_usd),
            'matched_buy_amount_ton': float(matched_buy),
            'profit_ton': float(profit_ton),
            'profit_usd': float(profit_usd),
            'tax_rate': float(TAX_RATE_PROFIT),
            'tax_amount_ton': float(tax_ton),
            'tax_amount_usd': float(tax_usd),
        })

    # Вымышленные сделки для демонстрации (пример с покупкой/продажей 1000 TON).
    # Используем один месяц (например, декабрь 2025), чтобы показать,
    # как считается налог 5% от положительной разницы между покупкой и продажей.
    demo_deals = []
    demo_tax_ton = Decimal('0')
    demo_tax_usd = Decimal('0')

    if year == 2025 and month == 12:
        amount_demo_ton = Decimal('1000')
        # Берём текущий курс как "цена покупки"
        buy_price = ton_price_usd
        # Для демонстрации считаем, что на следующий день курс вырос на 10%
        sell_price = (ton_price_usd * Decimal('1.10')).quantize(Decimal('0.00000001'))

        buy_usd = amount_demo_ton * buy_price
        sell_usd = amount_demo_ton * sell_price
        profit_usd = sell_usd - buy_usd  # прибыль в USD

        if profit_usd > 0:
            tax_usd = (profit_usd * TAX_RATE_PROFIT).quantize(Decimal('0.00000001'))
        else:
            tax_usd = Decimal('0')

        # Налог в TON по курсу продажи
        tax_ton = (tax_usd / sell_price).quantize(Decimal('0.000000001')) if tax_usd > 0 else Decimal('0')

        demo_deals = [
            {
                'operation_type': 'buy',
                'date': '11.12.2025',
                'amount_ton': float(amount_demo_ton),
                'amount_usd': float(buy_usd),
                'price_usd': float(buy_price),
                'profit_ton': 0.0,
                'profit_usd': 0.0,
                'tax_rate': float(TAX_RATE_PROFIT),
                'tax_amount_ton': 0.0,
                'tax_amount_usd': 0.0,
            },
            {
                'operation_type': 'sell',
                'date': '12.12.2025',
                'amount_ton': float(amount_demo_ton),
                'amount_usd': float(sell_usd),
                'price_usd': float(sell_price),
                'profit_ton': float((profit_usd / sell_price).quantize(Decimal('0.000000001'))) if profit_usd > 0 else 0.0,
                'profit_usd': float(profit_usd),
                'tax_rate': float(TAX_RATE_PROFIT),
                'tax_amount_ton': float(tax_ton),
                'tax_amount_usd': float(tax_usd),
            },
        ]

        demo_tax_ton = tax_ton
        demo_tax_usd = tax_usd

    return {
        'year': year,
        'month': month,
        'total_sent_ton': float(total_sent_ton),
        'total_sent_usd': float(total_sent_usd),
        'total_tax_ton': float(demo_tax_ton),
        'total_tax_usd': float(demo_tax_usd),
        'transactions_count': len(transactions_detail),
        'transactions': transactions_detail,
        'demo_deals': demo_deals,
    }


def calculate_tax_for_all_months(wallet_address, start_year=None, start_month=None, ton_price_usd=None):
    first_tx = TransactionHistory.objects.filter(
        wallet_address=wallet_address
    ).order_by('timestamp').first()
    
    if not first_tx:
        return []
    
    last_tx = TransactionHistory.objects.filter(
        wallet_address=wallet_address
    ).order_by('-timestamp').first()
    
    if not last_tx:
        return []
    
    if start_year is None:
        start_year = first_tx.timestamp.year
    if start_month is None:
        start_month = first_tx.timestamp.month
    
    end_year = last_tx.timestamp.year
    end_month = last_tx.timestamp.month
    
    if ton_price_usd is None:
        ton_price_usd = get_ton_price_usd()
    
    tax_results = []
    current_year = start_year
    current_month = start_month
    
    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        tax_info = calculate_tax_for_month(wallet_address, current_year, current_month, ton_price_usd)
        # Раньше мы отбрасывали месяцы без исходящих транзакций.
        # Теперь всегда добавляем месяц, чтобы он отображался на фронте даже с нулевым налогом.
        tax_results.append(tax_info)
        
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    
    return tax_results


def calculate_total_tax(wallet_address, start_year=None, start_month=None, ton_price_usd=None):
    monthly_taxes = calculate_tax_for_all_months(wallet_address, start_year, start_month, ton_price_usd)
    
    total_tax_ton = sum(tax['total_tax_ton'] for tax in monthly_taxes)
    total_tax_usd = sum(tax['total_tax_usd'] for tax in monthly_taxes)
    total_sent_ton = sum(tax['total_sent_ton'] for tax in monthly_taxes)
    total_sent_usd = sum(tax['total_sent_usd'] for tax in monthly_taxes)
    total_transactions = sum(tax['transactions_count'] for tax in monthly_taxes)
    
    period = None
    if monthly_taxes:
        first_month = monthly_taxes[0]
        last_month = monthly_taxes[-1]
        period = {
            'start': f"{first_month['year']}-{first_month['month']:02d}",
            'end': f"{last_month['year']}-{last_month['month']:02d}"
        }
    
    if ton_price_usd is None:
        ton_price_usd = get_ton_price_usd()
    
    return {
        'total_tax_ton': float(total_tax_ton),
        'total_tax_usd': float(total_tax_usd),
        'total_sent_ton': float(total_sent_ton),
        'total_sent_usd': float(total_sent_usd),
        'total_transactions': total_transactions,
        'ton_price_usd': float(ton_price_usd),
        'monthly_taxes': monthly_taxes,
        'period': period
    }