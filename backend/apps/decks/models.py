"""
Модель колоды (Deck) — тематический набор флэш-карточек.
"""

from django.db import models
from django.contrib.auth.models import User


class Deck(models.Model):
    """Колода карточек."""

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='decks',
        verbose_name='Владелец'
    )
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, default='', verbose_name='Описание')
    is_public = models.BooleanField(default=False, verbose_name='Публичная')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Колода'
        verbose_name_plural = 'Колоды'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

    @property
    def cards_count(self):
        """Общее количество карточек в колоде."""
        return self.cards.count()

    def cards_due_count(self, user):
        """Количество карточек, требующих повторения сегодня."""
        from django.utils import timezone
        from apps.reviews.models import ReviewLog

        today = timezone.now().date()
        # Карточки с просроченным повторением
        due_cards = ReviewLog.objects.filter(
            card__deck=self,
            user=user,
            next_review__lte=today,
        ).values('card').distinct().count()
        # Новые карточки (без записей повторений)
        reviewed_card_ids = ReviewLog.objects.filter(
            card__deck=self, user=user
        ).values_list('card_id', flat=True)
        new_cards = self.cards.exclude(id__in=reviewed_card_ids).count()
        return due_cards + new_cards
