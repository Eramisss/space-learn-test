"""
API-представления для статистики и аналитики.
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from django.db.models.functions import TruncDate
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.cards.models import Card
from apps.reviews.models import ReviewLog


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def overview(request):
    """
    GET /api/stats/overview/
    Общая статистика пользователя.
    Формат ответа подобран под фронтенд (StatsPage в frontend/index.html).
    """
    user = request.user
    today = timezone.now().date()

    total_cards = Card.objects.filter(deck__owner=user).count()

    reviewed_ids = set(
        ReviewLog.objects.filter(user=user).values_list('card_id', flat=True).distinct()
    )
    reviewed_cards = len(reviewed_ids)
    new_cards = total_cards - reviewed_cards

    # Средний EF по всем записям повторений
    avg_ef = ReviewLog.objects.filter(user=user).aggregate(
        avg=Avg('easiness_factor')
    )['avg'] or 2.5

    # Карточки, которые сегодня нужно повторить (просроченные + новые в пределах лимита)
    due_today = ReviewLog.objects.filter(
        user=user, next_review__lte=today
    ).values('card').distinct().count() + min(new_cards, 20)

    # История повторений за 30 дней — массив {day, review_count}
    start_date = today - timedelta(days=30)
    daily = ReviewLog.objects.filter(
        user=user, reviewed_at__date__gte=start_date,
    ).annotate(
        d=TruncDate('reviewed_at')
    ).values('d').annotate(
        review_count=Count('id')
    ).order_by('d')

    daily_history = [
        {'day': item['d'].isoformat(), 'review_count': item['review_count']}
        for item in daily
    ]

    return Response({
        'total_cards': total_cards,
        'reviewed_cards': reviewed_cards,
        'new_cards': new_cards,
        'due_today': due_today,
        'average_ef': round(avg_ef, 2),
        'daily_history': daily_history,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def history(request):
    """
    GET /api/stats/history/
    История повторений по дням (последние 30 дней).
    """
    user = request.user
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)

    daily_stats = ReviewLog.objects.filter(
        user=user,
        reviewed_at__date__gte=start_date,
    ).annotate(
        date=TruncDate('reviewed_at')
    ).values('date').annotate(
        total_reviews=Count('id'),
        avg_quality=Avg('quality'),
        failed=Count('id', filter=Q(quality__lt=3)),
        success=Count('id', filter=Q(quality__gte=3)),
    ).order_by('date')

    return Response({
        'period_days': days,
        'data': list(daily_stats),
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def heatmap(request):
    """
    GET /api/stats/heatmap/
    Календарь активности (количество повторений за каждый день, 365 дней).
    """
    user = request.user
    start_date = timezone.now().date() - timedelta(days=365)

    daily_counts = ReviewLog.objects.filter(
        user=user,
        reviewed_at__date__gte=start_date,
    ).annotate(
        date=TruncDate('reviewed_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    return Response({
        'data': list(daily_counts),
    })
