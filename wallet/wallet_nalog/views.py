from django.contrib.auth import login
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes 
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from pytoniq_core import Address
from .models import WalletSession, TransactionHistory, User
from .tonservice import save_wallet_to_db, account_info, save_transactions_to_db, get_history_transaction
from .serializers import UserLoginSerializer, UserRegistrationSerializer, UserSerializer, WalletSessionSerializer, WalletSessionUpdateSerializer
from .tax_calculator import calculate_tax_for_month, calculate_tax_for_all_months, calculate_total_tax
import asyncio
import json
import os
import logging
import threading

logger = logging.getLogger(__name__)

def wallet_test_page(request):
    return render(request, 'wallet_nalog/wallet_test.html')

def tonconnect_manifest(request):
    # Обработка OPTIONS запроса для CORS preflight
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin'
        response['Access-Control-Max-Age'] = '3600'
        return response
    
    # Получаем базовый URL из запроса
    # Важно: для ngrok используем HTTPS
    protocol = 'https' if request.is_secure() or 'ngrok' in request.get_host() else 'http'
    host = request.get_host()
    base_url = f"{protocol}://{host}"
    
    # Формируем манифест согласно спецификации TON Connect
    # Обязательные поля: url, name, iconUrl
    manifest = {
        "url": base_url,
        "name": "TON Wallet Test",
        "iconUrl": "https://ton.org/favicon.ico"
    }
    
    # Создаем JSON ответ без дополнительных параметров форматирования
    response = JsonResponse(manifest)
    response['Content-Type'] = 'application/json'
    # CORS заголовки для TON Connect (критично для мобильных приложений)
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin'
    response['Access-Control-Max-Age'] = '3600'
    # Отключаем кеширование для манифеста
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@api_view(['POST'])
@permission_classes([AllowAny])
def Registration(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        tokens = user.generate_tokens()
        response_serializer = UserSerializer(user, context={'request': request})
        response_data = response_serializer.data
        response_data['tokens'] = tokens
        return Response(response_data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def Login(request):
    serializer = UserLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    # Для JWT аутентификации сессионный login не требуется
    tokens = user.generate_tokens()
    response_serializer = UserSerializer(user, context={'request': request})
    response_data = response_serializer.data
    response_data['tokens'] = tokens
    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def RefreshToken(request):
    """Обновление access токена с помощью refresh токена"""
    refresh_token = request.data.get('refresh_token')
    
    if not refresh_token:
        return Response(
            {'error': 'refresh_token обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = User.verify_refresh_token(refresh_token)
    
    if not user:
        return Response(
            {'error': 'Неверный или истекший refresh токен'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Генерируем новые токены
    tokens = user.generate_tokens()
    
    return Response({
        'tokens': tokens
    }, status=status.HTTP_200_OK)

@api_view(['Get', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def connect_wallet(request):
    if request.method == 'GET':
        wallet_session = request.user.wallet
        if wallet_session and wallet_session.connected:
            serializer = WalletSessionSerializer(wallet_session)
            data = serializer.data

            # Нормализуем адрес кошелька в формат UQ... (base64, non-bounceable),
            # чтобы он совпадал с адресом в Tonkeeper.
            raw_address = wallet_session.wallet_address
            try:
                addr_obj = Address(raw_address)
                friendly_address = addr_obj.to_str(is_bounceable=False)
                data['wallet_address'] = friendly_address
            except Exception:
                # Если что‑то пошло не так, оставляем как есть
                pass

            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'message': 'Кошелек не подключен', 'connected': False},
                status=status.HTTP_200_OK
            )
    
    elif request.method == 'POST':
        wallet_address = request.data.get('wallet_address')
        wallet_type = request.data.get('wallet_type', 'TON')
        
        if not wallet_address:
            return Response(
                {'error': 'Адрес кошелька обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if save_wallet_to_db(request.user, wallet_address, wallet_type):
            wallet_session = request.user.wallet
            serializer = WalletSessionSerializer(wallet_session)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Ошибка при сохранении кошелька'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    elif request.method == 'PUT':
        wallet_session = request.user.wallet
        if not wallet_session:
            return Response(
                {'error': 'Кошелек не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = WalletSessionUpdateSerializer(wallet_session, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tax_for_month(request):
    wallet_session = request.user.wallet
    
    if not wallet_session or not wallet_session.connected:
        return Response(
            {'error': 'Кошелек не подключен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    # Нормализуем адрес в тот же формат, в котором он хранится в БД (UQ...)
    wallet_address = wallet_session.wallet_address
    try:
        wallet_address = Address(wallet_address).to_str(is_bounceable=False)
    except Exception:
        pass
    
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    
    if not year or not month:
        return Response(
            {'error': 'Необходимо указать параметры year и month'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        year = int(year)
        month = int(month)
        
        if month < 1 or month > 12:
            return Response(
                {'error': 'Месяц должен быть от 1 до 12'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tax_info = calculate_tax_for_month(wallet_address, year, month)
        return Response(tax_info, status=status.HTTP_200_OK)
    
    except ValueError:
        return Response(
            {'error': 'Год и месяц должны быть числами'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Ошибка при расчете налога: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tax_for_all_months(request):
    wallet_session = request.user.wallet
    
    if not wallet_session or not wallet_session.connected:
        return Response(
            {'error': 'Кошелек не подключен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    # Нормализуем адрес в формат UQ..., чтобы совпадал с записями TransactionHistory
    wallet_address = wallet_session.wallet_address
    try:
        wallet_address = Address(wallet_address).to_str(is_bounceable=False)
    except Exception:
        pass
    
    start_year = request.query_params.get('start_year')
    start_month = request.query_params.get('start_month')
    
    try:
        if start_year:
            start_year = int(start_year)
        if start_month:
            start_month = int(start_month)
            if start_month < 1 or start_month > 12:
                return Response(
                    {'error': 'Месяц должен быть от 1 до 12'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        monthly_taxes = calculate_tax_for_all_months(
            wallet_address,
            start_year=start_year,
            start_month=start_month
        )
        
        return Response({
            'monthly_taxes': monthly_taxes,
            'count': len(monthly_taxes)
        }, status=status.HTTP_200_OK)
    
    except ValueError:
        return Response(
            {'error': 'Год и месяц должны быть числами'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Ошибка при расчете налога: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_total_tax(request):
    wallet_session = request.user.wallet
    
    if not wallet_session or not wallet_session.connected:
        return Response(
            {'error': 'Кошелек не подключен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    # Нормализуем адрес в формат UQ..., как в TransactionHistory
    wallet_address = wallet_session.wallet_address
    try:
        wallet_address = Address(wallet_address).to_str(is_bounceable=False)
    except Exception:
        pass
    start_year = request.query_params.get('start_year')
    start_month = request.query_params.get('start_month')
    
    try:
        if start_year:
            start_year = int(start_year)
        if start_month:
            start_month = int(start_month)
            if start_month < 1 or start_month > 12:
                return Response(
                    {'error': 'Месяц должен быть от 1 до 12'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        tax_summary = calculate_total_tax(
            wallet_address,
            start_year=start_year,
            start_month=start_month
        )
        
        return Response(tax_summary, status=status.HTTP_200_OK)
    
    except ValueError:
        return Response(
            {'error': 'Год и месяц должны быть числами'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Ошибка при расчете налога: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_balance(request):
    wallet_session = request.user.wallet
    
    if not wallet_session or not wallet_session.connected:
        return Response(
            {'error': 'Кошелек не подключен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    wallet_address = wallet_session.wallet_address
    
    try:
        info = asyncio.run(account_info(wallet_address))
        
        if info is None:
            return Response(
                {'error': 'Не удалось получить информацию о кошельке'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'address': info['address'],
            'balance': info['balance'],
            'is_active': info['is_active'],
            'balance_ton': f"{info['balance']:.9f}"
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении баланса: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_transactions(request):
    wallet_session = request.user.wallet
    
    if not wallet_session or not wallet_session.connected:
        return Response(
            {'error': 'Кошелек не подключен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    wallet_address = wallet_session.wallet_address
    force_refresh = request.query_params.get('refresh', 'false').lower() == 'true'
    
    try:
        logger.info(f"Запрос транзакций для адреса: {wallet_address}, force_refresh: {force_refresh}")
        # Нормализуем адрес в удобный формат (UQ...) и дальше ВСЮДЫ используем его –
        # и для выборки из БД, и для сохранения, и для ответа фронту.
        def normalize_address(addr: str) -> str:
            if not addr:
                return ''
            try:
                return Address(addr).to_str(is_bounceable=False)
            except Exception:
                return addr

        normalized_wallet_address = normalize_address(wallet_address)

        if not force_refresh:
            db_transactions = TransactionHistory.objects.filter(
                wallet_address=normalized_wallet_address
            ).order_by('-timestamp')[:50]
            
            if db_transactions.exists():
                transactions_data = []
                for tx in db_transactions:
                    transactions_data.append({
                        'tx_hash': tx.tx_hash,
                        'timestamp': tx.timestamp.isoformat() if tx.timestamp else None,
                        'amount': float(tx.amount),
                        'amount_ton': f"{tx.amount:.9f}",
                        'from_address': normalize_address(tx.from_address),
                        'to_address': normalize_address(tx.to_address),
                        'status': tx.status,
                        'created_at': tx.created_at.isoformat() if tx.created_at else None,
                    })
                
                logger.info(f"Возвращаем {len(transactions_data)} транзакций из БД")
                
                def update_transactions_background():
                    try:
                        logger.info(f"Начало фонового обновления транзакций для {normalized_wallet_address}")
                        transactions = asyncio.run(get_history_transaction(normalized_wallet_address))
                        logger.info(f"Получено транзакций из блокчейна: {len(transactions)}")
                        saved_count = save_transactions_to_db(normalized_wallet_address, transactions)
                        logger.info(f"Сохранено транзакций в БД: {saved_count}")
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении транзакций в фоне: {e}", exc_info=True)
                
                thread = threading.Thread(target=update_transactions_background, daemon=True)
                thread.start()
                
                return Response({
                    'transactions': transactions_data,
                    'count': len(transactions_data),
                    'loaded_from_blockchain': 0,
                    'saved_to_db': 0,
                    'from_cache': True
                }, status=status.HTTP_200_OK)
        
        logger.info("Транзакций в БД нет, загружаем из блокчейна...")
        transactions = asyncio.run(get_history_transaction(normalized_wallet_address))
        logger.info(f"Получено транзакций из блокчейна: {len(transactions)}")
        
        saved_count = save_transactions_to_db(normalized_wallet_address, transactions)
        logger.info(f"Сохранено транзакций в БД: {saved_count}")
        
        db_transactions = TransactionHistory.objects.filter(
            wallet_address=normalized_wallet_address
        ).order_by('-timestamp')[:50]
        
        logger.info(f"Транзакций в БД для адреса {wallet_address}: {db_transactions.count()}")
        
        transactions_data = []
        for tx in db_transactions:
            transactions_data.append({
                'tx_hash': tx.tx_hash,
                'timestamp': tx.timestamp.isoformat() if tx.timestamp else None,
                'amount': float(tx.amount),
                'amount_ton': f"{tx.amount:.9f}",
                'from_address': normalize_address(tx.from_address),
                'to_address': normalize_address(tx.to_address),
                'status': tx.status,
                'created_at': tx.created_at.isoformat() if tx.created_at else None,
            })
        
        logger.info(f"Возвращаем {len(transactions_data)} транзакций")
        
        return Response({
            'transactions': transactions_data,
            'count': len(transactions_data),
            'loaded_from_blockchain': len(transactions),
            'saved_to_db': saved_count,
            'from_cache': False
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Ошибка при получении транзакций: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return Response(
            {'error': f'Ошибка при получении транзакций: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )