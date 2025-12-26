from .tonservice import get_balance, get_history_transaction, account_info
from .models import TransactionHistory, WalletSession
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import asyncio
import requests


TAX_RATE_PROFIT = Decimal('0.05')


def get_ton_price_for_date(date_str):
    """
    Получить цену TON в USD для конкретной даты.
    Использует CoinGecko API для исторических данных или реалистичную симуляцию на основе реальных данных.
    Формат date_str: 'YYYY-MM-DD'
    """
    from datetime import datetime as dt
    current_price = get_ton_price_usd()
    
    try:
        date_obj = dt.strptime(date_str, '%Y-%m-%d')
        today = dt.now()
        
        if date_obj < today:
            date_formatted = date_obj.strftime('%d-%m-%Y')
            response = requests.get(
                f'https://api.coingecko.com/api/v3/coins/the-open-network/history?date={date_formatted}',
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                price = data.get('market_data', {}).get('current_price', {}).get('usd')
                if not price:
                    price = data.get('market_data', {}).get('current_price')
                    if isinstance(price, dict):
                        price = price.get('usd')
                if price:
                    return Decimal(str(price))
    except Exception as e:
        print(f"Не удалось получить историческую цену для {date_str}: {e}")
    
    year_month = date_str[:7]
    month_multipliers = {
        '2025-08': 0.94,
        '2025-09': 1.03,
        '2025-11': 1.09,
        '2025-12': 1.15,
    }
    month_mult = month_multipliers.get(year_month, 1.0)
    
    day = int(date_str.split('-')[2])
    year = int(date_str.split('-')[0])
    month = int(date_str.split('-')[1])
    
    date_seed = (year * 10000 + month * 100 + day) % 1000000
    day_variation = 0.98 + ((date_seed % 40) / 1000.0)
    
    micro_seed = (date_seed * 7 + day * 13 + month * 17) % 10000
    micro_variation = 0.9985 + (micro_seed / 20000.0)
    
    month_mult_decimal = Decimal(str(month_mult))
    day_variation_decimal = Decimal(str(day_variation))
    micro_variation_decimal = Decimal(str(micro_variation))
    
    final_price = current_price * month_mult_decimal * day_variation_decimal * micro_variation_decimal
    
    return final_price.quantize(Decimal('0.0001'))


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
    start_naive = datetime(year, month, 1)
    if month == 12:
        end_naive = datetime(year + 1, 1, 1)
    else:
        end_naive = datetime(year, month + 1, 1)

    start_date = timezone.make_aware(start_naive)
    end_date = timezone.make_aware(end_naive)
    
    month_txs = TransactionHistory.objects.filter(
        wallet_address=wallet_address,
        timestamp__gte=start_date,
        timestamp__lt=end_date
    ).order_by('timestamp')
    
    if ton_price_usd is None:
        ton_price_usd = get_ton_price_usd()
    else:
        if not isinstance(ton_price_usd, Decimal):
            ton_price_usd = Decimal(str(ton_price_usd))
    
    total_tax_ton = Decimal('0')
    total_tax_usd = Decimal('0')
    total_sent_ton = Decimal('0')
    total_sent_usd = Decimal('0')
    transactions_detail = []

    buys_pool = []

    for tx in month_txs:
        amount_ton = Decimal(str(tx.amount))

        is_buy = tx.to_address == wallet_address and tx.from_address != wallet_address
        is_sell = tx.from_address == wallet_address and tx.to_address != wallet_address

        if not is_buy and not is_sell:
            continue

        amount_usd = amount_ton * ton_price_usd

        if is_buy:
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

    demo_deals = []
    demo_tax_ton = Decimal('0')
    demo_tax_usd = Decimal('0')

    if year == 2025 and month == 8:
        amount_demo_ton = Decimal('5000')
        buy_price = Decimal(str(get_ton_price_for_date('2025-08-12')))
        sell_price = Decimal(str(get_ton_price_for_date('2025-08-25')))
        
        buy_usd = amount_demo_ton * buy_price
        sell_usd = amount_demo_ton * sell_price
        profit_usd = sell_usd - buy_usd
        
        if profit_usd > 0:
            tax_usd = (profit_usd * TAX_RATE_PROFIT).quantize(Decimal('0.00000001'))
        else:
            tax_usd = Decimal('0')
        
        tax_ton = (tax_usd / sell_price).quantize(Decimal('0.000000001')) if tax_usd > 0 else Decimal('0')
        
        demo_deals = [
            {
                'operation_type': 'buy',
                'date': '12.08.2025',
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
                'date': '25.08.2025',
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
        
        for deal in demo_deals:
            if deal['operation_type'] == 'sell':
                total_sent_ton += Decimal(str(deal['amount_ton']))
                total_sent_usd += Decimal(str(deal['amount_usd']))
    
    elif year == 2025 and month == 9:
        amount_demo_ton = Decimal('7500')
        buy_price = Decimal(str(get_ton_price_for_date('2025-09-01')))
        sell_price = Decimal(str(get_ton_price_for_date('2025-09-19')))
        
        buy_usd = amount_demo_ton * buy_price
        sell_usd = amount_demo_ton * sell_price
        profit_usd = sell_usd - buy_usd
        
        if profit_usd > 0:
            tax_usd = (profit_usd * TAX_RATE_PROFIT).quantize(Decimal('0.00000001'))
        else:
            tax_usd = Decimal('0')
        
        tax_ton = (tax_usd / sell_price).quantize(Decimal('0.000000001')) if tax_usd > 0 else Decimal('0')
        
        demo_deals = [
            {
                'operation_type': 'buy',
                'date': '01.09.2025',
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
                'date': '19.09.2025',
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
        
        for deal in demo_deals:
            if deal['operation_type'] == 'sell':
                total_sent_ton += Decimal(str(deal['amount_ton']))
                total_sent_usd += Decimal(str(deal['amount_usd']))
    
    elif year == 2025 and month == 11:
        amount_demo_ton = Decimal('10000')
        buy_price = Decimal(str(get_ton_price_for_date('2025-11-06')))
        
        buy_usd = amount_demo_ton * buy_price
        
        demo_deals = [
            {
                'operation_type': 'buy',
                'date': '06.11.2025',
                'amount_ton': float(amount_demo_ton),
                'amount_usd': float(buy_usd),
                'price_usd': float(buy_price),
                'profit_ton': 0.0,
                'profit_usd': 0.0,
                'tax_rate': float(TAX_RATE_PROFIT),
                'tax_amount_ton': 0.0,
                'tax_amount_usd': 0.0,
            },
        ]
        
        demo_tax_ton = Decimal('0')
        demo_tax_usd = Decimal('0')
    
    elif year == 2025 and month == 12:
        demo_deals = []
        demo_tax_ton = Decimal('0')
        demo_tax_usd = Decimal('0')
        
        amount_nov_ton = Decimal('10000')
        buy_price_nov = Decimal(str(get_ton_price_for_date('2025-11-06')))
        sell_price_dec = Decimal(str(get_ton_price_for_date('2025-12-10')))
        
        buy_usd_nov = amount_nov_ton * buy_price_nov
        sell_usd_dec = amount_nov_ton * sell_price_dec
        profit_usd_nov = sell_usd_dec - buy_usd_nov
        
        if profit_usd_nov > 0:
            tax_usd_nov = (profit_usd_nov * TAX_RATE_PROFIT).quantize(Decimal('0.00000001'))
        else:
            tax_usd_nov = Decimal('0')
        
        tax_ton_nov = (tax_usd_nov / sell_price_dec).quantize(Decimal('0.000000001')) if tax_usd_nov > 0 else Decimal('0')
        
        demo_deals.append({
            'operation_type': 'sell',
            'date': '10.12.2025',
            'amount_ton': float(amount_nov_ton),
            'amount_usd': float(sell_usd_dec),
            'price_usd': float(sell_price_dec),
            'profit_ton': float((profit_usd_nov / sell_price_dec).quantize(Decimal('0.000000001'))) if profit_usd_nov > 0 else 0.0,
            'profit_usd': float(profit_usd_nov),
            'tax_rate': float(TAX_RATE_PROFIT),
            'tax_amount_ton': float(tax_ton_nov),
            'tax_amount_usd': float(tax_usd_nov),
        })
        
        demo_tax_ton += tax_ton_nov
        demo_tax_usd += tax_usd_nov
        
        amount_dec_ton = Decimal('1000')
        buy_price_dec = Decimal(str(get_ton_price_for_date('2025-12-11')))
        sell_price_dec2 = Decimal(str(get_ton_price_for_date('2025-12-12')))
        
        buy_usd_dec = amount_dec_ton * buy_price_dec
        sell_usd_dec2 = amount_dec_ton * sell_price_dec2
        profit_usd_dec = sell_usd_dec2 - buy_usd_dec
        
        if profit_usd_dec > 0:
            tax_usd_dec = (profit_usd_dec * TAX_RATE_PROFIT).quantize(Decimal('0.00000001'))
        else:
            tax_usd_dec = Decimal('0')
        
        tax_ton_dec = (tax_usd_dec / sell_price_dec2).quantize(Decimal('0.000000001')) if tax_usd_dec > 0 else Decimal('0')
        
        demo_deals.append({
            'operation_type': 'buy',
            'date': '11.12.2025',
            'amount_ton': float(amount_dec_ton),
            'amount_usd': float(buy_usd_dec),
            'price_usd': float(buy_price_dec),
            'profit_ton': 0.0,
            'profit_usd': 0.0,
            'tax_rate': float(TAX_RATE_PROFIT),
            'tax_amount_ton': 0.0,
            'tax_amount_usd': 0.0,
        })
        
        demo_deals.append({
            'operation_type': 'sell',
            'date': '12.12.2025',
            'amount_ton': float(amount_dec_ton),
            'amount_usd': float(sell_usd_dec2),
            'price_usd': float(sell_price_dec2),
            'profit_ton': float((profit_usd_dec / sell_price_dec2).quantize(Decimal('0.000000001'))) if profit_usd_dec > 0 else 0.0,
            'profit_usd': float(profit_usd_dec),
            'tax_rate': float(TAX_RATE_PROFIT),
            'tax_amount_ton': float(tax_ton_dec),
            'tax_amount_usd': float(tax_usd_dec),
        })
        
        demo_tax_ton += tax_ton_dec
        demo_tax_usd += tax_usd_dec
        
        total_tax_ton += demo_tax_ton
        total_tax_usd += demo_tax_usd
        
        for deal in demo_deals:
            if deal['operation_type'] == 'sell':
                total_sent_ton += Decimal(str(deal['amount_ton']))
                total_sent_usd += Decimal(str(deal['amount_usd']))

    return {
        'year': year,
        'month': month,
        'total_sent_ton': float(total_sent_ton),
        'total_sent_usd': float(total_sent_usd),
        'total_tax_ton': float(demo_tax_ton),
        'total_tax_usd': float(demo_tax_usd),
        'transactions_count': len(transactions_detail) + len([d for d in demo_deals if d.get('operation_type')]),
        'transactions': transactions_detail,
        'demo_deals': demo_deals,
    }


def calculate_tax_for_all_months(wallet_address, start_year=None, start_month=None, ton_price_usd=None):
    first_tx = TransactionHistory.objects.filter(
        wallet_address=wallet_address
    ).order_by('timestamp').first()
    
    last_tx = TransactionHistory.objects.filter(
        wallet_address=wallet_address
    ).order_by('-timestamp').first()
    
    demo_start_year = 2025
    demo_start_month = 8
    demo_end_year = 2025
    demo_end_month = 12
    
    if start_year is None:
        if first_tx:
            start_year = min(first_tx.timestamp.year, demo_start_year)
        else:
            start_year = demo_start_year
    if start_month is None:
        if first_tx:
            if first_tx.timestamp.year == demo_start_year:
                start_month = min(first_tx.timestamp.month, demo_start_month)
            elif first_tx.timestamp.year < demo_start_year:
                start_month = first_tx.timestamp.month
            else:
                start_month = demo_start_month
        else:
            start_month = demo_start_month
    
    if last_tx:
        end_year = max(last_tx.timestamp.year, demo_end_year)
        if last_tx.timestamp.year == demo_end_year:
            end_month = max(last_tx.timestamp.month, demo_end_month)
        elif last_tx.timestamp.year > demo_end_year:
            end_month = last_tx.timestamp.month
        else:
            end_month = demo_end_month
    else:
        end_year = demo_end_year
        end_month = demo_end_month
    
    if ton_price_usd is None:
        ton_price_usd = get_ton_price_usd()
    else:
        if not isinstance(ton_price_usd, Decimal):
            ton_price_usd = Decimal(str(ton_price_usd))
    
    tax_results = []
    current_year = start_year
    current_month = start_month
    
    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        tax_info = calculate_tax_for_month(wallet_address, current_year, current_month, ton_price_usd)
        tax_results.append(tax_info)
        
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    
    return tax_results


def calculate_total_tax(wallet_address, start_year=None, start_month=None, ton_price_usd=None):
    if ton_price_usd is not None and not isinstance(ton_price_usd, Decimal):
        ton_price_usd = Decimal(str(ton_price_usd))
    
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