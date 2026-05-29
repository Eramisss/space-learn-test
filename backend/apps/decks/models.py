"""
Модель колоды (Deck) — тематический набор флэш-карточек,
а также социальные модели: оценки (DeckRating) и предложения
улучшений к чужим публичным колодам (Suggestion).
"""

from django.db import models
from django.db.models import Avg
from django.core.validators import MinValueValidator, MaxValueValidator
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

    @property
    def avg_rating(self):
        """Средняя оценка колоды (1–5) или None, если оценок ещё нет."""
        result = self.ratings.aggregate(avg=Avg('score'))['avg']
        return round(result, 2) if result is not None else None

    @property
    def ratings_count(self):
        """Количество выставленных оценок."""
        return self.ratings.count()

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


class DeckRating(models.Model):
    """
    Оценка публичной колоды пользователем: балл 1–5 и необязательный отзыв.
    Один пользователь — одна оценка на колоду (можно изменить).
    """

    deck = models.ForeignKey(
        Deck, on_delete=models.CASCADE, related_name='ratings',
        verbose_name='Колода'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='deck_ratings',
        verbose_name='Пользователь'
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка (1–5)'
    )
    comment = models.TextField(blank=True, default='', verbose_name='Отзыв')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Оценка колоды'
        verbose_name_plural = 'Оценки колод'
        ordering = ['-updated_at']
        # Один пользователь оценивает колоду только один раз
        constraints = [
            models.UniqueConstraint(fields=['deck', 'user'], name='unique_deck_rating'),
        ]

    def __str__(self):
        return f'{self.user.username} → {self.deck.title}: {self.score}'


class Suggestion(models.Model):
    """
    Предложение улучшения к чужой публичной колоде: добавить новую
    карточку, изменить существующую или удалить её. Модерирует владелец.
    """

    TYPE_ADD = 'add'
    TYPE_EDIT = 'edit'
    TYPE_DELETE = 'delete'
    TYPE_CHOICES = [
        (TYPE_ADD, 'Добавить карточку'),
        (TYPE_EDIT, 'Изменить карточку'),
        (TYPE_DELETE, 'Удалить карточку'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает рассмотрения'),
        (STATUS_ACCEPTED, 'Принято'),
        (STATUS_REJECTED, 'Отклонено'),
    ]

    deck = models.ForeignKey(
        Deck, on_delete=models.CASCADE, related_name='suggestions',
        verbose_name='Колода'
    )
    # Карточка-цель для edit/delete; для add остаётся пустой.
    # SET_NULL — чтобы предложение сохранялось как история даже после удаления карточки.
    card = models.ForeignKey(
        'cards.Card', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='suggestions', verbose_name='Карточка'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='suggestions',
        verbose_name='Автор предложения'
    )
    suggestion_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, verbose_name='Тип предложения'
    )
    # Предлагаемый текст карточки (для add/edit)
    front = models.TextField(blank=True, default='', verbose_name='Лицевая сторона')
    back = models.TextField(blank=True, default='', verbose_name='Оборотная сторона')
    comment = models.TextField(blank=True, default='', verbose_name='Комментарий автора')
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING,
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата рассмотрения')

    class Meta:
        verbose_name = 'Предложение улучшения'
        verbose_name_plural = 'Предложения улучшений'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author.username} → {self.deck.title} ({self.get_suggestion_type_display()})'
