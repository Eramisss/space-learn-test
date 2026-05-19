"""
API-представления для управления карточками.
"""

from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.decks.models import Deck
from .models import Card
from .serializers import CardSerializer, CardCreateSerializer, CSVImportSerializer


class CardViewSet(viewsets.ModelViewSet):
    """
    CRUD для карточек внутри колоды.
    GET    /api/cards/deck/{deck_id}/     — список карточек в колоде
    POST   /api/cards/deck/{deck_id}/     — создание карточки
    GET    /api/cards/{id}/               — детали карточки
    PUT    /api/cards/{id}/               — обновление
    DELETE /api/cards/{id}/               — удаление
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == 'create':
            return CardCreateSerializer
        return CardSerializer

    def get_queryset(self):
        deck_id = self.kwargs.get('deck_id')
        if deck_id:
            return Card.objects.filter(deck_id=deck_id, deck__owner=self.request.user)
        return Card.objects.filter(deck__owner=self.request.user)

    def perform_create(self, serializer):
        deck_id = self.kwargs.get('deck_id')
        deck = Deck.objects.get(id=deck_id, owner=self.request.user)
        serializer.save(deck=deck)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def import_csv(request, deck_id):
    """
    POST /api/decks/{deck_id}/import/
    Массовый импорт карточек.
    Body: {"cards": [{"front": "...", "back": "..."}, ...]}
    """
    try:
        deck = Deck.objects.get(id=deck_id, owner=request.user)
    except Deck.DoesNotExist:
        return Response(
            {'error': 'Колода не найдена.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    cards_data = request.data.get('cards') or []
    if not isinstance(cards_data, list) or not cards_data:
        return Response(
            {'error': 'Ожидается поле "cards" со списком карточек.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    to_create = []
    for item in cards_data:
        front = (item.get('front') or '').strip()
        back = (item.get('back') or '').strip()
        if front and back:
            to_create.append(Card(deck=deck, front=front, back=back))

    Card.objects.bulk_create(to_create)
    return Response(
        {'message': f'Импортировано {len(to_create)} карточек.', 'count': len(to_create)},
        status=status.HTTP_201_CREATED,
    )
