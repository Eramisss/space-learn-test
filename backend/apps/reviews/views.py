"""
API-представления для процесса повторения карточек.
"""

from django.utils import timezone
from django.db.models import Subquery, OuterRef
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.cards.models import Card
from apps.decks.models import Deck
from .models import ReviewLog, SM2Engine
from .serializers import ReviewSubmitSerializer, ReviewResultSerializer, CardForReviewSerializer


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def today_cards(request):
    """
    GET /api/review/today/
    Получение списка карточек для повторения сегодня.

    Алгоритм выборки:
    1. Карточки с next_review <= сегодня (из review_logs)
    2. Новые карточки (без записей повторений), лимит 20
    3. Сортировка: сначала просроченные, затем новые
    """
    user = request.user
    today = timezone.now().date()
    deck_id = request.query_params.get('deck_id')

    # Базовый queryset карточек пользователя
    user_cards = Card.objects.filter(deck__owner=user)
    if deck_id:
        user_cards = user_cards.filter(deck_id=deck_id)

    # Последние записи повторений для каждой карточки
    latest_reviews = ReviewLog.objects.filter(
        user=user, card=OuterRef('pk')
    ).order_by('-reviewed_at')

    # 1. Карточки, требующие повторения (next_review <= today)
    due_card_ids = ReviewLog.objects.filter(
        user=user,
        next_review__lte=today,
        card__deck__owner=user,
    )
    if deck_id:
        due_card_ids = due_card_ids.filter(card__deck_id=deck_id)

    # Берём только последний review для каждой карточки
    due_card_ids = due_card_ids.values('card').annotate(
        max_reviewed=Subquery(
            ReviewLog.objects.filter(
                user=user, card=OuterRef('card')
            ).order_by('-reviewed_at').values('reviewed_at')[:1]
        )
    ).filter(
        reviewed_at=Subquery(
            ReviewLog.objects.filter(
                user=user, card=OuterRef('card')
            ).order_by('-reviewed_at').values('reviewed_at')[:1]
        ),
        next_review__lte=today,
    ).values_list('card_id', flat=True)

    due_cards = user_cards.filter(id__in=due_card_ids)

    # 2. Новые карточки (без записей повторений)
    reviewed_card_ids = ReviewLog.objects.filter(
        user=user
    ).values_list('card_id', flat=True).distinct()
    new_cards = user_cards.exclude(id__in=reviewed_card_ids)

    # Лимит новых карточек
    daily_limit = getattr(user, 'profile', None)
    limit = daily_limit.daily_new_cards_limit if daily_limit else 20
    new_cards = new_cards[:limit]

    # Формирование ответа
    result = []

    for card in due_cards:
        last_review = ReviewLog.objects.filter(
            user=user, card=card
        ).order_by('-reviewed_at').first()
        result.append({
            'id': card.id,
            'front': card.front,
            'back': card.back,
            'deck_id': card.deck_id,
            'deck_title': card.deck.title,
            'is_new': False,
            'current_ef': last_review.easiness_factor if last_review else 2.5,
            'current_interval': last_review.interval_days if last_review else 0,
        })

    for card in new_cards:
        result.append({
            'id': card.id,
            'front': card.front,
            'back': card.back,
            'deck_id': card.deck_id,
            'deck_title': card.deck.title,
            'is_new': True,
            'current_ef': 2.5,
            'current_interval': 0,
        })

    serializer = CardForReviewSerializer(result, many=True)
    # Фронт ожидает плоский массив карточек
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_review(request, card_id):
    """
    POST /api/review/{card_id}/
    Отправка результата повторения карточки.

    Body: { "quality": 0-5 }

    Вызывает алгоритм SM-2 для пересчёта параметров.
    """
    serializer = ReviewSubmitSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    quality = serializer.validated_data['quality']

    try:
        card = Card.objects.get(id=card_id, deck__owner=request.user)
    except Card.DoesNotExist:
        return Response(
            {'error': 'Карточка не найдена.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Вызов алгоритма SM-2
    review_log = SM2Engine.process_review(
        user=request.user,
        card=card,
        quality=quality,
    )

    # Формат подобран под фронтенд: res.sm2_result.{interval, easiness_factor}
    return Response({
        'card_id': card.id,
        'quality': quality,
        'sm2_result': {
            'interval': review_log.interval_days,
            'easiness_factor': round(review_log.easiness_factor, 2),
            'repetitions': review_log.repetitions,
            'next_review': review_log.next_review,
        },
    })
