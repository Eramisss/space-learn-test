"""
Автоматизированные модульные тесты для алгоритма SM-2.

Тестовый план:
1. Тест расчёта EF при различных оценках (q = 0..5)
2. Тест ограничения EF (минимум 1.3)
3. Тест расчёта интервалов (I(1) = 1, I(2) = 6, I(n) = I(n-1)*EF)
4. Тест сброса при q < 3
5. Тест полного цикла повторений
6. Тест для новой карточки (нет предыдущих записей)
"""

from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from apps.decks.models import Deck
from apps.cards.models import Card
from apps.reviews.models import ReviewLog, SM2Engine


class SM2EngineCalculateEFTest(TestCase):
    """Тесты расчёта коэффициента лёгкости (EF)."""

    def test_ef_with_quality_5(self):
        """При q=5 EF должен увеличиться."""
        new_ef = SM2Engine.calculate_ef(2.5, 5)
        self.assertAlmostEqual(new_ef, 2.6, places=2)

    def test_ef_with_quality_4(self):
        """При q=4 EF не изменяется значительно."""
        new_ef = SM2Engine.calculate_ef(2.5, 4)
        self.assertAlmostEqual(new_ef, 2.5, places=2)

    def test_ef_with_quality_3(self):
        """При q=3 EF уменьшается."""
        new_ef = SM2Engine.calculate_ef(2.5, 3)
        self.assertAlmostEqual(new_ef, 2.36, places=2)

    def test_ef_with_quality_0(self):
        """При q=0 EF сильно уменьшается."""
        new_ef = SM2Engine.calculate_ef(2.5, 0)
        self.assertAlmostEqual(new_ef, 1.7, places=2)

    def test_ef_minimum_bound(self):
        """EF не может быть меньше 1.3."""
        # Несколько неудачных ответов подряд
        ef = 1.4
        new_ef = SM2Engine.calculate_ef(ef, 0)
        self.assertGreaterEqual(new_ef, 1.3)

    def test_ef_minimum_enforced(self):
        """Даже при очень низком начальном EF, результат >= 1.3."""
        new_ef = SM2Engine.calculate_ef(1.3, 0)
        self.assertEqual(new_ef, 1.3)


class SM2EngineCalculateIntervalTest(TestCase):
    """Тесты расчёта интервалов повторения."""

    def test_first_repetition(self):
        """I(1) = 1 день."""
        interval = SM2Engine.calculate_interval(1, 2.5, 0)
        self.assertEqual(interval, 1)

    def test_second_repetition(self):
        """I(2) = 6 дней."""
        interval = SM2Engine.calculate_interval(2, 2.5, 1)
        self.assertEqual(interval, 6)

    def test_third_repetition(self):
        """I(3) = round(6 * EF) = round(6 * 2.5) = 15."""
        interval = SM2Engine.calculate_interval(3, 2.5, 6)
        self.assertEqual(interval, 15)

    def test_fourth_repetition(self):
        """I(4) = round(15 * 2.5) = 38."""
        interval = SM2Engine.calculate_interval(4, 2.5, 15)
        self.assertEqual(interval, 38)

    def test_interval_with_low_ef(self):
        """Интервал с низким EF (1.3)."""
        interval = SM2Engine.calculate_interval(3, 1.3, 6)
        self.assertEqual(interval, 8)  # round(6 * 1.3) = 8


class SM2EngineProcessReviewTest(TestCase):
    """Интеграционные тесты полного цикла SM-2."""

    def setUp(self):
        """Создание тестовых данных."""
        self.user = User.objects.create_user(
            username='testuser', email='test@test.com', password='testpass123'
        )
        self.deck = Deck.objects.create(
            owner=self.user, title='Тестовая колода'
        )
        self.card = Card.objects.create(
            deck=self.deck, front='Что такое Python?',
            back='Высокоуровневый язык программирования'
        )

    def test_new_card_first_review(self):
        """Первое повторение новой карточки (q=4)."""
        log = SM2Engine.process_review(self.user, self.card, quality=4)

        self.assertEqual(log.repetitions, 1)
        self.assertEqual(log.interval_days, 1)
        self.assertAlmostEqual(log.easiness_factor, 2.5, places=1)
        self.assertEqual(log.next_review, timezone.now().date() + timedelta(days=1))

    def test_successful_review_sequence(self):
        """Последовательность успешных повторений (q=4, q=4, q=5)."""
        # 1-е повторение
        log1 = SM2Engine.process_review(self.user, self.card, quality=4)
        self.assertEqual(log1.interval_days, 1)
        self.assertEqual(log1.repetitions, 1)

        # 2-е повторение
        log2 = SM2Engine.process_review(self.user, self.card, quality=4)
        self.assertEqual(log2.interval_days, 6)
        self.assertEqual(log2.repetitions, 2)

        # 3-е повторение
        log3 = SM2Engine.process_review(self.user, self.card, quality=5)
        self.assertEqual(log3.repetitions, 3)
        self.assertGreater(log3.interval_days, 6)

    def test_failed_review_resets(self):
        """При q < 3 сбрасываются repetitions и interval."""
        # Успешные повторения
        SM2Engine.process_review(self.user, self.card, quality=5)
        SM2Engine.process_review(self.user, self.card, quality=4)

        # Неудачный ответ
        log = SM2Engine.process_review(self.user, self.card, quality=2)
        self.assertEqual(log.repetitions, 0)
        self.assertEqual(log.interval_days, 1)

    def test_ef_never_below_minimum(self):
        """EF не опускается ниже 1.3 при множестве неудачных ответов."""
        for _ in range(10):
            SM2Engine.process_review(self.user, self.card, quality=0)

        last_log = ReviewLog.objects.filter(
            user=self.user, card=self.card
        ).order_by('-reviewed_at').first()

        self.assertGreaterEqual(last_log.easiness_factor, 1.3)

    def test_quality_0_complete_forget(self):
        """q=0: полное забывание — сброс + EF уменьшается."""
        log = SM2Engine.process_review(self.user, self.card, quality=0)
        self.assertEqual(log.repetitions, 0)
        self.assertEqual(log.interval_days, 1)
        self.assertLess(log.easiness_factor, 2.5)


class ReviewLogModelTest(TestCase):
    """Тесты модели ReviewLog."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser2', email='test2@test.com', password='testpass123'
        )
        self.deck = Deck.objects.create(owner=self.user, title='Тест')
        self.card = Card.objects.create(
            deck=self.deck, front='front', back='back'
        )

    def test_review_log_creation(self):
        """Запись ReviewLog корректно создаётся."""
        log = ReviewLog.objects.create(
            user=self.user,
            card=self.card,
            quality=4,
            easiness_factor=2.5,
            interval_days=1,
            repetitions=1,
            next_review=timezone.now().date() + timedelta(days=1),
        )
        self.assertIsNotNone(log.reviewed_at)
        self.assertEqual(log.quality, 4)

    def test_review_log_ordering(self):
        """Записи сортируются по reviewed_at в обратном порядке."""
        log1 = SM2Engine.process_review(self.user, self.card, quality=4)
        log2 = SM2Engine.process_review(self.user, self.card, quality=5)

        logs = ReviewLog.objects.filter(user=self.user, card=self.card)
        self.assertEqual(logs.first().pk, log2.pk)  # Последний — первый
