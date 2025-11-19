from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import WalletSession, TransactionHistory

User = get_user_model()


# Регистрация модели User
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'wallet_info', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email',)
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Кошелек', {
            'fields': ('wallet',),
        }),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    
    def wallet_info(self, obj):
        if obj.wallet:
            wallet_info = []
            if obj.wallet.wallet_address:
                wallet_info.append(f"Адрес: {obj.wallet.wallet_address}")
            if obj.wallet.wallet_type:
                wallet_info.append(f"Тип: {obj.wallet.wallet_type}")
            wallet_info.append(f"Подключен: {'Да' if obj.wallet.connected else 'Нет'}")
            return " | ".join(wallet_info) if wallet_info else "Кошелек создан"
        return "Нет кошелька"
    wallet_info.short_description = 'Информация о кошельке'


@admin.register(WalletSession)
class WalletSessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'wallet_address', 'wallet_type', 'connected', 'created_at', 'user_email')
    list_filter = ('connected', 'wallet_type', 'created_at')
    search_fields = ('session_key', 'wallet_address', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('session_key', 'wallet_address', 'wallet_type', 'connected')
        }),
        ('Связанный пользователь', {
            'fields': ('user',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def user_email(self, obj):
        """Отображает email пользователя"""
        return obj.user.email if obj.user else '-'
    user_email.short_description = 'Email пользователя'
    user_email.admin_order_field = 'user__email'


@admin.register(TransactionHistory)
class TransactionHistoryAdmin(admin.ModelAdmin):
    list_display = ('tx_hash_short', 'wallet_address', 'amount', 'from_address_short', 'to_address_short', 'status', 'timestamp', 'created_at')
    list_filter = ('status', 'timestamp', 'created_at')
    search_fields = ('tx_hash', 'wallet_address', 'from_address', 'to_address')
    readonly_fields = ('created_at',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('tx_hash', 'wallet_address', 'amount', 'status')
        }),
        ('Адреса', {
            'fields': ('from_address', 'to_address')
        }),
        ('Даты', {
            'fields': ('timestamp', 'created_at')
        }),
    )
    
    def tx_hash_short(self, obj):
        return f"{obj.tx_hash[:16]}..." if obj.tx_hash else '-'
    tx_hash_short.short_description = 'Хеш транзакции'
    
    def from_address_short(self, obj):
        return f"{obj.from_address[:16]}..." if obj.from_address else '-'
    from_address_short.short_description = 'От'
    
    def to_address_short(self, obj):
        return f"{obj.to_address[:16]}..." if obj.to_address else '-'
    to_address_short.short_description = 'Кому'
