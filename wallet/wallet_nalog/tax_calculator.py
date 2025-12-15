from .tonservice import get_balance, get_history_transaction, account_info
from .models import TransactionHistory, WalletSession
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
import asyncio
import requests


TAX_THRESHOLD_USD = Decimal('5000')
TAX_RATE_LOW = Decimal('0.01')  
TAX_RATE_HIGH = Decimal('0.005')


def get_ton_price_usd():
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


def calculate_tax_for_transaction(amount_ton, ton_price_usd=None):
    if ton_price_usd is None:
        ton_price_usd = get_ton_price_usd()
    
    amount_ton_decimal = Decimal(str(amount_ton))
    amount_usd = amount_ton_decimal * ton_price_usd
    
    if amount_usd < TAX_THRESHOLD_USD:
        tax_rate = TAX_RATE_LOW
    else:
        tax_rate = TAX_RATE_HIGH
    
    tax_amount_ton = amount_ton_decimal * tax_rate
    tax_amount_usd = amount_usd * tax_rate
    
    return {
        'amount_ton': float(amount_ton_decimal),
        'amount_usd': float(amount_usd),
        'tax_rate': float(tax_rate),
        'tax_amount_ton': float(tax_amount_ton),
        'tax_amount_usd': float(tax_amount_usd)
    }


def calculate_tax_for_month(wallet_address, year, month, ton_price_usd=None):
    # Используем timezone-aware даты, совместимые с Django
    start_naive = datetime(year, month, 1)
    if month == 12:
        end_naive = datetime(year + 1, 1, 1)
    else:
        end_naive = datetime(year, month + 1, 1)

    # Делаем aware в соответствии с настройками TIME_ZONE
    start_date = timezone.make_aware(start_naive)
    end_date = timezone.make_aware(end_naive)
    
    outgoing_transactions = TransactionHistory.objects.filter(
        wallet_address=wallet_address,
        from_address=wallet_address,
        timestamp__gte=start_date,
        timestamp__lt=end_date
    ).order_by('timestamp')
    
    if not outgoing_transactions.exists():
        return {
            'year': year,
            'month': month,
            'total_sent_ton': 0.0,
            'total_sent_usd': 0.0,
            'total_tax_ton': 0.0,
            'total_tax_usd': 0.0,
            'transactions_count': 0,
            'transactions': []
        }
    
    if ton_price_usd is None:
        ton_price_usd = get_ton_price_usd()
    
    total_tax_ton = Decimal('0')
    total_tax_usd = Decimal('0')
    total_sent_ton = Decimal('0')
    total_sent_usd = Decimal('0')
    transactions_detail = []
    
    for tx in outgoing_transactions:
        amount_ton = Decimal(str(tx.amount))
        tax_info = calculate_tax_for_transaction(amount_ton, ton_price_usd)
        
        total_tax_ton += Decimal(str(tax_info['tax_amount_ton']))
        total_tax_usd += Decimal(str(tax_info['tax_amount_usd']))
        total_sent_ton += amount_ton
        total_sent_usd += Decimal(str(tax_info['amount_usd']))
        
        transactions_detail.append({
            'tx_hash': tx.tx_hash,
            'timestamp': tx.timestamp.isoformat(),
            'amount_ton': tax_info['amount_ton'],
            'amount_usd': tax_info['amount_usd'],
            'tax_rate': tax_info['tax_rate'],
            'tax_amount_ton': tax_info['tax_amount_ton'],
            'tax_amount_usd': tax_info['tax_amount_usd']
        })
    
    return {
        'year': year,
        'month': month,
        'total_sent_ton': float(total_sent_ton),
        'total_sent_usd': float(total_sent_usd),
        'total_tax_ton': float(total_tax_ton),
        'total_tax_usd': float(total_tax_usd),
        'transactions_count': len(transactions_detail),
        'transactions': transactions_detail
    }


def calculate_tax_for_all_months(wallet_address, start_year=None, start_month=None, ton_price_usd=None):
    first_tx = TransactionHistory.objects.filter(
        wallet_address=wallet_address,
        from_address=wallet_address
    ).order_by('timestamp').first()
    
    if not first_tx:
        return []
    
    last_tx = TransactionHistory.objects.filter(
        wallet_address=wallet_address,
        from_address=wallet_address
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