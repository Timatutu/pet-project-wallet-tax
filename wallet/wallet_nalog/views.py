from django.contrib.auth import login
from rest_framework.decorators import api_view, permission_classes 
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .serializers import UserRegistrationSerializer, UserSerializer, UserLoginSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def Registration(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        tokens = user.generate_tokens()
        response_serializer = UserSerializer(user, context={'request': request})
        response_data = response_serializer.data
        response_data['tokens'] = tokens
        return Response(response_data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def Login(request):
    serializer = UserLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    login(request, user)
    tokens = user.generate_tokens()
    response_serializer = UserSerializer(user, context={'request': request})
    response_data = response_serializer.data
    response_data['tokens'] = tokens
    return Response(response_data, status=status.HTTP_200_OK)

