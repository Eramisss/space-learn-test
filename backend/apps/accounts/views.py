"""
API-представления для аутентификации и управления профилем.
"""

from django.contrib.auth import authenticate
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.decks.starter_decks import seed_starter_decks
from .serializers import RegisterSerializer, ProfileSerializer


def _user_payload(user):
    """Единый формат пользователя для ответов API."""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
    }


def _issue_token(user):
    """Выдать access-токен (используется как поле `token` в ответе)."""
    return str(RefreshToken.for_user(user).access_token)


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Регистрация нового пользователя. После создания пользователю
    автоматически выдаётся набор стартовых колод (см. apps.decks.starter_decks).
    Возвращает {token, user} — тот же формат, что и login.
    """
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            seed_starter_decks(user)
        except Exception as e:
            print(f'[seed_starter_decks] failed for user {user.id}: {e}')
        return Response(
            {'token': _issue_token(user), 'user': _user_payload(user)},
            status=status.HTTP_201_CREATED,
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """
    POST /api/auth/login/
    Body: {username, password}
    Ответ: {token, user}
    """
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''
    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {'error': 'Неверное имя пользователя или пароль'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return Response({'token': _issue_token(user), 'user': _user_payload(user)})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    """
    GET /api/auth/me/
    Возвращает данные текущего пользователя по JWT-токену.
    """
    return Response(_user_payload(request.user))


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/auth/profile/ — получение профиля текущего пользователя.
    PATCH /api/auth/profile/ — обновление профиля.
    """
    serializer_class = ProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user.profile
