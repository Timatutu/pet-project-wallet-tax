# serializers.py
from dataclasses import fields
import email
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import User, Wallet

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['wallet_id', 'balance', 'nalog', 'status_nalog', 'created_at']
        read_only_fields = ['wallet_id', 'created_at']

class UserSerializer(serializers.ModelSerializer):
    wallet = WalletSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'wallet', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm']
    
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
        
class WalletUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance', 'nalog', 'status_nalog']