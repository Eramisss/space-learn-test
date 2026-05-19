"""
Модели приложения accounts.
Используем стандартную модель User из Django с расширением через Profile.
"""

from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """
    Профиль пользователя — дополнительные поля к стандартной модели User.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, default='', verbose_name='О себе')
    daily_new_cards_limit = models.PositiveIntegerField(
        default=20,
        verbose_name='Лимит новых карточек в день'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль {self.user.username}'
