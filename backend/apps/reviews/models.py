"""
Модель ReviewLog и реализация алгоритма SM-2.

Алгоритм SM-2 (SuperMemo 2, Piotr Wozniak, 1987):
- Интервалы: I(1) = 1, I(2) = 6, I(n) = I(n-1) * EF
- Пересчёт EF: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
- Если q < 3: сброс повторений, интервал = 1 день
- Ограничение: EF >= 1.3
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from apps.cards.models import Card


class ReviewLog(models.Model):
    """
    Запись повторения карточки.
    Хранит результат каждого повторения и рассчитанные параметры SM-2.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reviews',
        verbose_name='Пользователь'
    )
    card = models.ForeignKey(
        Card, on_delete=models.CASCADE, related_name='reviews',
        verbose_name='Карточка'
    )

    # Оценка качества ответа (0-5)
    QUALITY_CHOICES = [
        (0, 'Полное забывание'),
        (1, 'Плохо'),
        (2, 'Неудовлетворительно'),
        (3, 'Удовлетворительно'),
        (4, 'Хорошо'),
        (5, 'Отлично'),
    ]
    quality = models.SmallIntegerField(
        choices=QUALITY_CHOICES,
        verbose_name='Оценка качества ответа'
    )

    # Параметры SM-2 после данного повторения
    easiness_factor = models.FloatField(
        default=2.5,
        verbose_name='Коэффициент лёгкости (EF)'
    )
    interval_days = models.PositiveIntegerField(
        default=1,
        verbose_name='Интервал (дни)'
    )
    repetitions = models.PositiveIntegerField(
        default=0,
        verbose_name='Номер повторения'
    )
    next_review = models.DateField(
        verbose_name='Дата следующего повторения'
    )
    reviewed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата и время повторения'
    )

    class Meta:
        verbose_name = 'Запись повторения'
        verbose_name_plural = 'Записи повторений'
        ordering = ['-reviewed_at']
        # Индекс для быстрой выборки карточек на повторение
        indexes = [
            models.Index(fields=['user', 'next_review']),
            models.Index(fields=['user', 'card', '-reviewed_at']),
        ]

    def __str__(self):
        return f'{self.user.username} → {self.card.front[:30]} (q={self.quality})'


class SM2Engine:
    """
    Реализация алгоритма интервальных повторений SM-2.

    Алгоритм:
    1. После ответа пользователя (оценка q от 0 до 5):
       - Пересчитать EF: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
       - Если EF' < 1.3, установить EF' = 1.3
    2. Если q >= 3 (успешный ответ):
       - n = n + 1
       - I(1) = 1 день, I(2) = 6 дней, I(n>2) = I(n-1) * EF
    3. Если q < 3 (неудачный ответ):
       - Сбросить n = 0, I = 1 день
       - EF не изменяется (сохраняется предыдущее значение)
    """

    @staticmethod
    def calculate_ef(current_ef: float, quality: int) -> float:
        """
        Пересчёт коэффициента лёгкости (Easiness Factor).

        Формула: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))

        Args:
            current_ef: текущий EF (>= 1.3)
            quality: оценка качества ответа (0-5)

        Returns:
            Новый EF (минимум 1.3)
        """
        new_ef = current_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        return max(new_ef, 1.3)

    @staticmethod
    def calculate_interval(repetitions: int, ef: float, prev_interval: int) -> int:
        """
        Расчёт интервала до следующего повторения.

        I(1) = 1, I(2) = 6, I(n) = round(I(n-1) * EF)

        Args:
            repetitions: новый номер повторения (после инкремента)
            ef: текущий EF
            prev_interval: предыдущий интервал в днях

        Returns:
            Новый интервал в днях
        """
        if repetitions == 1:
            return 1
        elif repetitions == 2:
            return 6
        else:
            return max(1, round(prev_interval * ef))

    @classmethod
    def process_review(cls, user: User, card: Card, quality: int) -> ReviewLog:
        """
        Обработка результата повторения карточки.

        Получает предыдущие параметры SM-2, рассчитывает новые
        и создаёт запись ReviewLog.

        Args:
            user: пользователь
            card: карточка
            quality: оценка качества ответа (0-5)

        Returns:
            Созданная запись ReviewLog
        """
        # Получить последнюю запись повторения
        last_review = ReviewLog.objects.filter(
            user=user, card=card
        ).order_by('-reviewed_at').first()

        if last_review:
            current_ef = last_review.easiness_factor
            current_reps = last_review.repetitions
            current_interval = last_review.interval_days
        else:
            # Новая карточка — начальные значения
            current_ef = 2.5
            current_reps = 0
            current_interval = 0

        # Пересчёт EF
        new_ef = cls.calculate_ef(current_ef, quality)

        # Определение нового интервала и количества повторений
        if quality >= 3:
            # Успешный ответ — увеличиваем интервал
            new_reps = current_reps + 1
            new_interval = cls.calculate_interval(new_reps, new_ef, current_interval)
        else:
            # Неудачный ответ — сброс
            new_reps = 0
            new_interval = 1

        # Дата следующего повторения
        next_review_date = timezone.now().date() + timedelta(days=new_interval)

        # Создание записи
        review_log = ReviewLog.objects.create(
            user=user,
            card=card,
            quality=quality,
            easiness_factor=round(new_ef, 4),
            interval_days=new_interval,
            repetitions=new_reps,
            next_review=next_review_date,
        )

        return review_log
