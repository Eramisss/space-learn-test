"""
API-представления для управления колодами, оценками и предложениями улучшений.
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import Deck, DeckRating, Suggestion
from .serializers import (
    DeckSerializer, DeckCreateSerializer,
    DeckRatingSerializer, SuggestionSerializer, SuggestionCreateSerializer,
)


def get_accessible_deck(user, deck_id):
    """
    Вернуть колоду, доступную пользователю: либо его собственную,
    либо чужую, но публичную. Иначе — 404.
    """
    return get_object_or_404(
        Deck.objects.filter(Q(owner=user) | Q(is_public=True)),
        pk=deck_id,
    )


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
    GET    /api/decks/public/    — публичные колоды (каталог)
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
        """Каталог публичных колод (для поиска и копирования)."""
        queryset = Deck.objects.filter(is_public=True).exclude(owner=request.user)
        search = request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(title__icontains=search)
        serializer = DeckSerializer(queryset[:50], many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='cards_preview',
            permission_classes=[permissions.IsAuthenticated])
    def cards_preview(self, request, pk=None):
        """Просмотр карточек доступной (своей или публичной) колоды — только чтение."""
        deck = get_accessible_deck(request.user, pk)
        cards = deck.cards.values('id', 'front', 'back')
        return Response(list(cards))

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def clone(self, request, pk=None):
        """Копирование публичной (или своей) колоды вместе с карточками."""
        source_deck = get_accessible_deck(request.user, pk)
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


# ─────────────────────────────────────────────────────────────
#  Оценки колод (рейтинги и отзывы)
# ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def deck_ratings(request, deck_id):
    """
    GET  /api/decks/{id}/ratings/ — список оценок + сводка (средняя, кол-во, моя).
    POST /api/decks/{id}/ratings/ — поставить/изменить свою оценку. Body: {score, comment}.
    """
    deck = get_accessible_deck(request.user, deck_id)

    if request.method == 'GET':
        ratings = deck.ratings.select_related('user').all()
        my = ratings.filter(user=request.user).first()
        return Response({
            'avg_rating': deck.avg_rating,
            'ratings_count': deck.ratings_count,
            'my_rating': DeckRatingSerializer(my).data if my else None,
            'ratings': DeckRatingSerializer(ratings, many=True).data,
        })

    # POST — нельзя оценивать собственную колоду
    if deck.owner_id == request.user.id:
        return Response(
            {'error': 'Нельзя оценивать собственную колоду.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    serializer = DeckRatingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    rating, _ = DeckRating.objects.update_or_create(
        deck=deck, user=request.user,
        defaults={
            'score': serializer.validated_data['score'],
            'comment': serializer.validated_data.get('comment', ''),
        },
    )
    return Response(DeckRatingSerializer(rating).data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
#  Предложения улучшений
# ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def deck_suggestions(request, deck_id):
    """
    GET  /api/decks/{id}/suggestions/ — список предложений.
         Владельцу видны все, остальным — только их собственные.
    POST /api/decks/{id}/suggestions/ — создать предложение.
    """
    deck = get_accessible_deck(request.user, deck_id)
    is_owner = deck.owner_id == request.user.id

    if request.method == 'GET':
        qs = deck.suggestions.select_related('author', 'card').all()
        if not is_owner:
            qs = qs.filter(author=request.user)
        return Response(SuggestionSerializer(qs, many=True).data)

    # POST — владельцу предлагать самому себе незачем
    if is_owner:
        return Response(
            {'error': 'Редактируйте свою колоду напрямую, без предложений.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    serializer = SuggestionCreateSerializer(data=request.data, context={'deck': deck})
    serializer.is_valid(raise_exception=True)
    suggestion = serializer.save(deck=deck, author=request.user)
    return Response(SuggestionSerializer(suggestion).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resolve_suggestion(request, suggestion_id):
    """
    POST /api/decks/suggestions/{id}/resolve/ — принять или отклонить предложение.
    Body: {"action": "accept" | "reject"}. Доступно только владельцу колоды.
    При принятии изменение применяется к карточкам колоды.
    """
    suggestion = get_object_or_404(
        Suggestion.objects.select_related('deck', 'card'), pk=suggestion_id
    )
    if suggestion.deck.owner_id != request.user.id:
        return Response(
            {'error': 'Только владелец колоды может рассматривать предложения.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if suggestion.status != Suggestion.STATUS_PENDING:
        return Response(
            {'error': 'Это предложение уже рассмотрено.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    action_name = request.data.get('action')
    if action_name not in ('accept', 'reject'):
        return Response(
            {'error': 'Поле "action" должно быть "accept" или "reject".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if action_name == 'accept':
        _apply_suggestion(suggestion)
        suggestion.status = Suggestion.STATUS_ACCEPTED
    else:
        suggestion.status = Suggestion.STATUS_REJECTED

    suggestion.resolved_at = timezone.now()
    suggestion.save(update_fields=['status', 'resolved_at'])
    return Response(SuggestionSerializer(suggestion).data)


def _apply_suggestion(suggestion):
    """Применить принятое предложение к карточкам колоды."""
    from apps.cards.models import Card

    if suggestion.suggestion_type == Suggestion.TYPE_ADD:
        Card.objects.create(
            deck=suggestion.deck,
            front=suggestion.front,
            back=suggestion.back,
        )
    elif suggestion.suggestion_type == Suggestion.TYPE_EDIT and suggestion.card_id:
        card = suggestion.card
        card.front = suggestion.front
        card.back = suggestion.back
        card.save(update_fields=['front', 'back'])
    elif suggestion.suggestion_type == Suggestion.TYPE_DELETE and suggestion.card_id:
        # Отвязываем карточку от предложения до удаления, иначе Django заблокирует
        # последующий save() предложения из-за «unsaved related object».
        card = suggestion.card
        suggestion.card = None
        card.delete()
