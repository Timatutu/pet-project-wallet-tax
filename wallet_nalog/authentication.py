import jwt
from django.conf import settings
from rest_framework import authentication, exceptions
from .models import User


class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return None
        
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            raise exceptions.AuthenticationFailed('Неверный формат токена. Используйте "Bearer <token>"')
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            if payload.get('token_type') != 'access':
                raise exceptions.AuthenticationFailed('Неверный тип токена')
            
            user_id = payload.get('user_id')
            if not user_id:
                raise exceptions.AuthenticationFailed('Токен не содержит user_id')
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('Пользователь не найден')
            
            if not user.is_active:
                raise exceptions.AuthenticationFailed('Пользователь неактивен')
            
            return (user, token)
            
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Токен истек')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Неверный токен')
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Ошибка аутентификации: {str(e)}')

