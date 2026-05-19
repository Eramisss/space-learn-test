"""
API-представления для управления колодами.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Deck
from .serializers import DeckSerializer, DeckCreateSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Разрешение: только владелец может редактировать."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class DeckViewSet(viewsets.ModelViewSet):
    """
    CRUD-операции для колод.
    GET    /api/decks/           — список колод пользователя
    POST   /api/decks/           — создание колоды
    GET    /api/decks/{id}/      — детали колоды
    PUT    /api/decks/{id}/      — обновление колоды
    DELETE /api/decks/{id}/      — удаление колоды
    GET    /api/decks/public/    — публичные колоды
    POST   /api/decks/{id}/clone/ — копирование публичной колоды
    """
    permission_classes = (permissions.IsAuthenticated, IsOwnerOrReadOnly)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return DeckCreateSerializer
        return DeckSerializer

    def get_queryset(self):
        return Deck.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def public(self, request):
        """Список публичных колод (для поиска и копирования)."""
        queryset = Deck.objects.filter(is_public=True).exclude(owner=request.user)
        search = request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(title__icontains=search)
        serializer = DeckSerializer(queryset[:50], many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def clone(self, request, pk=None):
        """Копирование публичной колоды вместе с карточками."""
        source_deck = self.get_object()
        if not source_deck.is_public and source_deck.owner != request.user:
            return Response(
                {'error': 'Колода не является публичной.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Создание копии
        new_deck = Deck.objects.create(
            owner=request.user,
            title=f'{source_deck.title} (копия)',
            description=source_deck.description,
            is_public=False,
        )
        # Копирование карточек
        from apps.cards.models import Card
        cards_to_create = []
        for card in source_deck.cards.all():
            cards_to_create.append(Card(
                deck=new_deck,
                front=card.front,
                back=card.back,
            ))
        Card.objects.bulk_create(cards_to_create)

        serializer = DeckSerializer(new_deck, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
