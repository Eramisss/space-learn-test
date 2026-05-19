"""
Модель карточки (Card) — единица учебного контента.
"""

from django.db import models
from apps.decks.models import Deck


class Card(models.Model):
    """
    Флэш-карточка: лицевая сторона (вопрос) и оборотная (ответ).
    """
    deck = models.ForeignKey(
        Deck, on_delete=models.CASCADE, related_name='cards',
        verbose_name='Колода'
    )
    front = models.TextField(verbose_name='Лицевая сторона (вопрос)')
    back = models.TextField(verbose_name='Оборотная сторона (ответ)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Карточка'
        verbose_name_plural = 'Карточки'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.front[:50]}...' if len(self.front) > 50 else self.front
