from django.urls import path
from .views import (
    Registration, 
    Login,
    RefreshToken,
    connect_wallet,
    get_tax_for_month,
    get_tax_for_all_months,
    get_total_tax,
    get_wallet_balance,
    get_wallet_transactions,
    wallet_test_page,
    index_page,
    tonconnect_manifest
)
from .tonservice import account_info

urlpatterns = [
    path('', index_page, name='index'),
    path('app/', index_page, name='app'),
    path('test/', wallet_test_page, name='wallet_test'),
    path('tonconnect-manifest.json', tonconnect_manifest, name='tonconnect_manifest'),
    path('register/', Registration, name='register'),
    path('login/', Login, name='login'),
    path('refresh/', RefreshToken, name='refresh_token'),
    path('Wallet/', connect_wallet, name='Wallet'),
    path('wallet/balance/', get_wallet_balance, name='wallet_balance'),
    path('wallet/transactions/', get_wallet_transactions, name='wallet_transactions'),
    path('tax/month/', get_tax_for_month, name='tax_month'),
    path('tax/all/', get_tax_for_all_months, name='tax_all_months'),
    path('tax/total/', get_total_tax, name='tax_total'),
]
