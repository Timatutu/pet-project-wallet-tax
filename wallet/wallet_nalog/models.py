from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


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
        
        return self.create_user(email, password, **extra_fields)


class Wallet(models.Model):
    class StatusNalog(models.TextChoices):
        NO = "NO", "НЕ ОПЛАЧЕН"
        YES = "YES", "ОПЛАЧЕН"
    
    wallet_id = models.CharField(max_length=100, unique=True)
    balance = models.FloatField(default=0)
    nalog = models.FloatField(default=0)
    status_nalog = models.CharField(
        max_length=20, 
        choices=StatusNalog.choices, 
        default=StatusNalog.NO
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Кошелек {self.wallet_id}"


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=100, unique=True)
    wallet = models.OneToOneField(
        Wallet, 
        on_delete=models.CASCADE,
        related_name='user'
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.pk:
            wallet = Wallet.objects.create(
                wallet_id=f"wallet_{int(timezone.now().timestamp())}"
            )
            self.wallet = wallet
        super().save(*args, **kwargs)