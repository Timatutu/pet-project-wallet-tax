# serializers.py
from dataclasses import fields
import email
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import User, WalletSession

class WalletSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletSession
        fields = ['session_key', 'wallet_address', 'wallet_type', 'connected', 'created_at', 'updated_at']
        read_only_fields = ['session_key', 'created_at', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
    wallet = WalletSessionSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'wallet', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, error_messages={
        'min_length': 'Пароль должен содержать минимум 8 символов.',
        'required': 'Пароль обязателен для заполнения.'
    })
    password_confirm = serializers.CharField(write_only=True, error_messages={
        'required': 'Подтверждение пароля обязательно.'
    })
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm']
        extra_kwargs = {
            'email': {
                'error_messages': {
                    'required': 'Email обязателен для заполнения.',
                    'invalid': 'Введите корректный email адрес.',
                }
            }
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            email=attrs['email'],
            password=attrs['password'],
        )
        if not user:
            raise serializers.ValidationError('Неверный email или пароль')
        attrs['user'] = user
        return attrs
        
class WalletSessionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletSession
        fields = ['wallet_address', 'wallet_type', 'connected']