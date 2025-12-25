# wallet_app/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings
import jwt

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise TypeError('Введите email!')
        if not password:
            raise TypeError('Введите пароль!')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        return self.create_user(email, password, **extra_fields)


class WalletSession(models.Model):
    session_key = models.CharField(max_length=100, unique=True, blank=True, null=True)
    wallet_address = models.CharField(max_length=100, blank=True, null=True)
    wallet_type = models.CharField(max_length=50, blank=True, null=True)
    connected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'wallet_sessions'
        verbose_name = 'Сессия кошелька'
        verbose_name_plural = 'Сессии кошельков'
        
    def __str__(self):
        return f"{self.wallet_address or 'No address'} - {self.session_key}"


class TransactionHistory(models.Model):
    wallet_address = models.CharField(max_length=100)
    tx_hash = models.CharField(max_length=100, unique=True)
    timestamp = models.DateTimeField()
    amount = models.DecimalField(max_digits=20, decimal_places=9)
    from_address = models.CharField(max_length=100)
    to_address = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'transaction_history'
        indexes = [
            models.Index(fields=['wallet_address', 'timestamp']),
            models.Index(fields=['tx_hash']),
        ]
        verbose_name = 'Транзакция'
        verbose_name_plural = 'История транзакций'
    
    def __str__(self):
        return f"{self.tx_hash[:16]}... - {self.amount} TON"


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=100, unique=True)
    wallet = models.OneToOneField(
        WalletSession, 
        on_delete=models.CASCADE,
        related_name='user',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.pk and not self.wallet:
            wallet = WalletSession.objects.create(
                session_key=f"user_{int(timezone.now().timestamp())}"
            )
            self.wallet = wallet
        super().save(*args, **kwargs)

    @property
    def token(self):
        return self._generate_access_token()

    def generate_tokens(self):
        return {
            'access': self._generate_access_token(),
            'refresh': self._generate_refresh_token()
        }

    def _generate_access_token(self):
        dt = datetime.now() + timedelta(minutes=15)  
        
        token = jwt.encode({
            'token_type': 'access', 
            'user_id': self.pk,      
            'email': self.email,
            'exp': int(dt.timestamp()),
            'iat': int(datetime.now().timestamp()),  
        }, settings.SECRET_KEY, algorithm='HS256')

        return token

    def _generate_refresh_token(self):
        dt = datetime.now() + timedelta(days=7)
        
        token = jwt.encode({
            'token_type': 'refresh',
            'user_id': self.pk,
            'exp': int(dt.timestamp()),
            'iat': int(datetime.now().timestamp()),
        }, settings.SECRET_KEY, algorithm='HS256')

        return token

    @classmethod
    def verify_refresh_token(cls, refresh_token):
        try:
            payload = jwt.decode(
                refresh_token, 
                settings.SECRET_KEY, 
                algorithms=['HS256']
            )
            
            if payload.get('token_type') != 'refresh':
                return None
                
            user_id = payload.get('user_id')
            if user_id:
                return cls.objects.get(id=user_id)
                
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, cls.DoesNotExist):
            return None
        
        return None

    def get_wallet_info(self):
        if self.wallet:
            return {
                'wallet_address': self.wallet.wallet_address,
                'wallet_type': self.wallet.wallet_type,
                'connected': self.wallet.connected,
                'session_key': self.wallet.session_key
            }
        return None

    def connect_wallet(self, wallet_address, wallet_type, session_key=None):
        if not self.wallet:
            self.wallet = WalletSession.objects.create()
        self.wallet.wallet_address = wallet_address
        self.wallet.wallet_type = wallet_type
        self.wallet.connected = True
        if session_key:
            self.wallet.session_key = session_key
        self.wallet.save()
        self.save()

    def disconnect_wallet(self):
        if self.wallet:
            self.wallet.wallet_address = None
            self.wallet.wallet_type = None
            self.wallet.connected = False
            self.wallet.save()