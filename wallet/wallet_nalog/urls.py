from django.urls import path
from .views import Registration, Login

urlpatterns = [
    path('register/', Registration, name='register'),
    path('login/', Login, name='login'),
]
