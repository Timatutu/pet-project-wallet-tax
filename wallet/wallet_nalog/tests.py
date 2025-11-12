from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User, Wallet


class RegistrationTests(APITestCase):
    def setUp(self):
        self.url = reverse('register')

    def test_successful_registration_creates_user_and_wallet(self):
        payload = {
            'email': 'new_user@example.com',
            'password': 'strongpassword',
            'password_confirm': 'strongpassword',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], payload['email'])
        self.assertIn('wallet', response.data)
        self.assertTrue(User.objects.filter(email=payload['email']).exists())
        user = User.objects.get(email=payload['email'])
        self.assertIsNotNone(user.wallet)
        self.assertEqual(user.wallet.balance, 0)
        self.assertEqual(user.wallet.status_nalog, Wallet.StatusNalog.NO)

    def test_registration_with_mismatched_passwords_returns_error(self):
        payload = {
            'email': 'user@example.com',
            'password': 'password123',
            'password_confirm': 'different123',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Пароли не совпадают', str(response.data))

    def test_registration_requires_unique_email(self):
        existing_user = User.objects.create_user(
            email='duplicate@example.com',
            password='strongpassword',
        )
        payload = {
            'email': existing_user.email,
            'password': 'anotherstrongpassword',
            'password_confirm': 'anotherstrongpassword',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_registration_rejects_short_password(self):
        payload = {
            'email': 'shortpass@example.com',
            'password': 'short',
            'password_confirm': 'short',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_registration_requires_email(self):
        payload = {
            'email': '',
            'password': 'strongpassword',
            'password_confirm': 'strongpassword',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_registration_rejects_invalid_email(self):
        payload = {
            'email': 'not-an-email',
            'password': 'strongpassword',
            'password_confirm': 'strongpassword',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_registration_response_contains_expected_fields(self):
        payload = {
            'email': 'fields@example.com',
            'password': 'strongpassword',
            'password_confirm': 'strongpassword',
        }

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertSetEqual(
            set(response.data.keys()),
            {'id', 'email', 'wallet', 'date_joined'},
        )
        wallet_data = response.data['wallet']
        self.assertSetEqual(
            set(wallet_data.keys()),
            {'wallet_id', 'balance', 'nalog', 'status_nalog', 'created_at'},
        )


class LoginTests(APITestCase):
    def setUp(self):
        self.url = reverse('login')
        self.password = 'strongpassword'
        self.user = User.objects.create_user(
            email='login_user@example.com',
            password=self.password,
        )

    def test_successful_login_returns_user_data(self):
        payload = {'email': self.user.email, 'password': self.password}

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertIn('wallet', response.data)

    def test_login_with_invalid_credentials_returns_error(self):
        payload = {'email': self.user.email, 'password': 'wrongpassword'}

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Неверный email или пароль', str(response.data))

    def test_login_with_unknown_email_returns_error(self):
        payload = {'email': 'unknown@example.com', 'password': self.password}

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Неверный email или пароль', str(response.data))

    def test_login_requires_password(self):
        payload = {'email': self.user.email, 'password': ''}

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_login_requires_email(self):
        payload = {'email': '', 'password': self.password}

        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)


class UserModelTests(APITestCase):
    def test_user_str_returns_email(self):
        user = User.objects.create_user(
            email='str_user@example.com',
            password='strongpassword',
        )

        self.assertEqual(str(user), 'str_user@example.com')

    def test_wallet_str_returns_identifier(self):
        wallet = Wallet.objects.create(wallet_id='wallet_123')

        self.assertEqual(str(wallet), 'Кошелек wallet_123')

    def test_wallet_created_when_user_saved(self):
        user = User.objects.create_user(
            email='wallet_user@example.com',
            password='strongpassword',
        )

        self.assertIsNotNone(user.wallet)
        self.assertTrue(user.wallet.wallet_id.startswith('wallet_'))
