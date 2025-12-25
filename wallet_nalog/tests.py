import jwt
import time
from datetime import datetime, timedelta
from django.urls import reverse
from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User, WalletSession


class RegistrationTests(APITestCase):
    """Тесты для регистрации пользователей"""
    
    def setUp(self):
        self.url = reverse('register')

    def test_successful_registration_creates_user_and_wallet_session(self):
        """Проверка успешной регистрации с созданием пользователя и сессии кошелька"""
        payload = {
            'email': 'new_user@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], payload['email'])
        self.assertIn('wallet', response.data)
        self.assertTrue(User.objects.filter(email=payload['email']).exists())
        user = User.objects.get(email=payload['email'])
        self.assertIsNotNone(user.wallet)
        self.assertIsInstance(user.wallet, WalletSession)

    def test_registration_with_mismatched_passwords_returns_error(self):
        """Проверка ошибки при несовпадении паролей"""
        payload = {
            'email': 'user@example.com',
            'password': 'password123',
            'password_confirm': 'different123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Пароли не совпадают', str(response.data))

    def test_registration_requires_unique_email(self):
        """Проверка уникальности email"""
        existing_user = User.objects.create_user(
            email='duplicate@example.com',
            password='strongpassword123',
        )
        payload = {
            'email': existing_user.email,
            'password': 'anotherstrongpassword123',
            'password_confirm': 'anotherstrongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_registration_rejects_short_password(self):
        """Проверка отклонения короткого пароля"""
        payload = {
            'email': 'shortpass@example.com',
            'password': 'short',
            'password_confirm': 'short',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_registration_requires_email(self):
        """Проверка обязательности email"""
        payload = {
            'email': '',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_registration_rejects_invalid_email(self):
        """Проверка отклонения невалидного email"""
        payload = {
            'email': 'not-an-email',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_registration_returns_jwt_tokens(self):
        """Проверка возврата JWT токенов при регистрации"""
        payload = {
            'email': 'jwt_reg@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

    def test_registration_access_token_is_valid(self):
        """Проверка валидности access токена при регистрации"""
        payload = {
            'email': 'jwt_reg_valid@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        access_token = response.data['tokens']['access']
        
        token_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(token_payload['token_type'], 'access')
        self.assertEqual(token_payload['email'], payload['email'])
        
        user = User.objects.get(email=payload['email'])
        self.assertEqual(token_payload['user_id'], user.id)

    def test_registration_refresh_token_is_valid(self):
        """Проверка валидности refresh токена при регистрации"""
        payload = {
            'email': 'jwt_reg_refresh@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        refresh_token = response.data['tokens']['refresh']
        
        token_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(token_payload['token_type'], 'refresh')
        
        user = User.objects.get(email=payload['email'])
        self.assertEqual(token_payload['user_id'], user.id)

    def test_registration_tokens_can_be_verified(self):
        """Проверка возможности верификации токенов после регистрации"""
        payload = {
            'email': 'jwt_reg_verify@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        refresh_token = response.data['tokens']['refresh']
        
        # Проверяем, что refresh токен можно верифицировать
        user = User.verify_refresh_token(refresh_token)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, payload['email'])

    def test_registration_access_token_expires_in_15_minutes(self):
        """Проверка срока действия access токена (15 минут)"""
        payload = {
            'email': 'jwt_reg_exp@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        access_token = response.data['tokens']['access']
        token_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])

        exp = datetime.fromtimestamp(token_payload['exp'])
        iat = datetime.fromtimestamp(token_payload['iat'])
        time_diff = exp - iat

        # Проверяем, что срок действия примерно 15 минут
        self.assertAlmostEqual(time_diff.total_seconds(), 15 * 60, delta=5)

    def test_registration_refresh_token_expires_in_7_days(self):
        """Проверка срока действия refresh токена (7 дней)"""
        payload = {
            'email': 'jwt_reg_refresh_exp@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        refresh_token = response.data['tokens']['refresh']
        token_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])

        exp = datetime.fromtimestamp(token_payload['exp'])
        iat = datetime.fromtimestamp(token_payload['iat'])
        time_diff = exp - iat

        # Проверяем, что срок действия примерно 7 дней
        self.assertAlmostEqual(time_diff.total_seconds(), 7 * 24 * 60 * 60, delta=10)

    def test_registration_does_not_return_tokens_on_error(self):
        """Проверка отсутствия токенов при ошибке регистрации"""
        payload = {
            'email': 'jwt_reg_error@example.com',
            'password': 'short',
            'password_confirm': 'short',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('tokens', response.data)

    def test_registration_response_contains_expected_fields(self):
        """Проверка наличия ожидаемых полей в ответе регистрации"""
        payload = {
            'email': 'fields@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertIn('email', response.data)
        self.assertIn('wallet', response.data)
        self.assertIn('date_joined', response.data)
        self.assertIn('tokens', response.data)


class LoginTests(APITestCase):
    """Тесты для входа пользователей"""
    
    def setUp(self):
        self.url = reverse('login')
        self.password = 'strongpassword123'
        self.user = User.objects.create_user(
            email='login_user@example.com',
            password=self.password,
        )

    def test_successful_login_returns_user_data(self):
        """Проверка успешного входа с возвратом данных пользователя"""
        payload = {'email': self.user.email, 'password': self.password}

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertIn('wallet', response.data)

    def test_login_with_invalid_credentials_returns_error(self):
        """Проверка ошибки при неверных учетных данных"""
        payload = {'email': self.user.email, 'password': 'wrongpassword'}

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Неверный email или пароль', str(response.data))

    def test_login_with_unknown_email_returns_error(self):
        """Проверка ошибки при неизвестном email"""
        payload = {'email': 'unknown@example.com', 'password': self.password}

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Неверный email или пароль', str(response.data))

    def test_login_requires_password(self):
        """Проверка обязательности пароля"""
        payload = {'email': self.user.email, 'password': ''}

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_login_requires_email(self):
        """Проверка обязательности email"""
        payload = {'email': '', 'password': self.password}

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_login_returns_jwt_tokens(self):
        """Проверка возврата JWT токенов при входе"""
        payload = {
            'email': self.user.email,
            'password': self.password,
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

    def test_login_access_token_is_valid(self):
        """Проверка валидности access токена при входе"""
        payload = {
            'email': self.user.email,
            'password': self.password,
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['tokens']['access']
        
        token_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(token_payload['token_type'], 'access')
        self.assertEqual(token_payload['email'], self.user.email)
        self.assertEqual(token_payload['user_id'], self.user.id)

    def test_login_refresh_token_is_valid(self):
        """Проверка валидности refresh токена при входе"""
        payload = {
            'email': self.user.email,
            'password': self.password,
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refresh_token = response.data['tokens']['refresh']
        
        token_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(token_payload['token_type'], 'refresh')
        self.assertEqual(token_payload['user_id'], self.user.id)

    def test_login_tokens_can_be_verified(self):
        """Проверка возможности верификации токенов после входа"""
        payload = {
            'email': self.user.email,
            'password': self.password,
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refresh_token = response.data['tokens']['refresh']
        
        # Проверяем, что refresh токен можно верифицировать
        verified_user = User.verify_refresh_token(refresh_token)
        self.assertIsNotNone(verified_user)
        self.assertEqual(verified_user.id, self.user.id)
        self.assertEqual(verified_user.email, self.user.email)

    def test_login_access_token_expires_in_15_minutes(self):
        """Проверка срока действия access токена (15 минут)"""
        payload = {
            'email': self.user.email,
            'password': self.password,
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['tokens']['access']
        token_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])

        exp = datetime.fromtimestamp(token_payload['exp'])
        iat = datetime.fromtimestamp(token_payload['iat'])
        time_diff = exp - iat

        # Проверяем, что срок действия примерно 15 минут
        self.assertAlmostEqual(time_diff.total_seconds(), 15 * 60, delta=5)

    def test_login_refresh_token_expires_in_7_days(self):
        """Проверка срока действия refresh токена (7 дней)"""
        payload = {
            'email': self.user.email,
            'password': self.password,
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refresh_token = response.data['tokens']['refresh']
        token_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])

        exp = datetime.fromtimestamp(token_payload['exp'])
        iat = datetime.fromtimestamp(token_payload['iat'])
        time_diff = exp - iat

        # Проверяем, что срок действия примерно 7 дней
        self.assertAlmostEqual(time_diff.total_seconds(), 7 * 24 * 60 * 60, delta=10)

    def test_login_does_not_return_tokens_on_invalid_credentials(self):
        """Проверка отсутствия токенов при неверных учетных данных"""
        payload = {
            'email': self.user.email,
            'password': 'wrongpassword',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('tokens', response.data)

    def test_login_tokens_are_different_on_each_login(self):
        """Проверка генерации разных токенов при каждом входе"""
        payload = {
            'email': self.user.email,
            'password': self.password,
        }

        response1 = self.client.post(self.url, data=payload, format='json')
        time.sleep(1)  # Задержка для разного времени генерации
        response2 = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        access_token1 = response1.data['tokens']['access']
        access_token2 = response2.data['tokens']['access']
        
        payload1 = jwt.decode(access_token1, settings.SECRET_KEY, algorithms=['HS256'])
        payload2 = jwt.decode(access_token2, settings.SECRET_KEY, algorithms=['HS256'])
        
        # Если токены сгенерированы в разные секунды, они должны быть разными
        if payload1['iat'] != payload2['iat']:
            self.assertNotEqual(access_token1, access_token2)

    def test_login_response_contains_expected_fields(self):
        """Проверка наличия ожидаемых полей в ответе входа"""
        payload = {
            'email': self.user.email,
            'password': self.password,
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)
        self.assertIn('email', response.data)
        self.assertIn('wallet', response.data)
        self.assertIn('date_joined', response.data)
        self.assertIn('tokens', response.data)

    def test_login_with_inactive_user_returns_error(self):
        """Проверка ошибки при входе неактивного пользователя"""
        self.user.is_active = False
        self.user.save()
        
        payload = {
            'email': self.user.email,
            'password': self.password,
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Неверный email или пароль', str(response.data))


class UserModelTests(APITestCase):
    """Тесты для модели User"""
    
    def test_user_str_returns_email(self):
        """Проверка строкового представления пользователя"""
        user = User.objects.create_user(
            email='str_user@example.com',
            password='strongpassword123',
        )

        self.assertEqual(str(user), 'str_user@example.com')

    def test_wallet_session_created_when_user_saved(self):
        """Проверка создания сессии кошелька при сохранении пользователя"""
        user = User.objects.create_user(
            email='wallet_user@example.com',
            password='strongpassword123',
        )

        self.assertIsNotNone(user.wallet)
        self.assertIsInstance(user.wallet, WalletSession)
        self.assertIsNotNone(user.wallet.session_key)
