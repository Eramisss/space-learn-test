"""
Модульные тесты алгоритма SM-2.

Тестируется:
1. Корректность расчёта коэффициента лёгкости (EF)
2. Корректность расчёта интервалов повторения
3. Поведение при различных оценках качества (0–5)
4. Граничные условия (EF не ниже 1.3)
5. Сброс прогресса при q < 3
6. Пример полного цикла повторений
"""

import sys
import os
import unittest
from datetime import date, timedelta

# Добавить путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from sm2 import (
    sm2_algorithm, calculate_easiness_factor, calculate_interval,
    SM2Result, DEFAULT_EASINESS_FACTOR, MIN_EASINESS_FACTOR, MAX_INTERVAL
)


class TestCalculateEasinessFactor(unittest.TestCase):
    """Тесты расчёта коэффициента лёгкости."""

    def test_perfect_answer_increases_ef(self):
        """Оценка 5 должна увеличить EF."""
        new_ef = calculate_easiness_factor(2.5, 5)
        self.assertGreater(new_ef, 2.5)

    def test_good_answer_keeps_ef(self):
        """Оценка 4 должна немного увеличить или сохранить EF."""
        new_ef = calculate_easiness_factor(2.5, 4)
        self.assertGreaterEqual(new_ef, 2.5)

    def test_satisfactory_answer_decreases_ef(self):
        """Оценка 3 должна уменьшить EF."""
        new_ef = calculate_easiness_factor(2.5, 3)
        self.assertLess(new_ef, 2.5)

    def test_bad_answer_decreases_ef_more(self):
        """Оценка 0 должна значительно уменьшить EF."""
        ef_q0 = calculate_easiness_factor(2.5, 0)
        ef_q3 = calculate_easiness_factor(2.5, 3)
        self.assertLess(ef_q0, ef_q3)

    def test_ef_never_below_minimum(self):
        """EF не должен опускаться ниже 1.3."""
        ef = 1.3
        for _ in range(10):
            ef = calculate_easiness_factor(ef, 0)
        self.assertGreaterEqual(ef, MIN_EASINESS_FACTOR)

    def test_ef_minimum_enforcement(self):
        """При очень низком EF результат всё равно >= 1.3."""
        new_ef = calculate_easiness_factor(1.3, 0)
        self.assertEqual(new_ef, MIN_EASINESS_FACTOR)

    def test_invalid_quality_raises_error(self):
        """Некорректная оценка должна вызвать ValueError."""
        with self.assertRaises(ValueError):
            calculate_easiness_factor(2.5, -1)
        with self.assertRaises(ValueError):
            calculate_easiness_factor(2.5, 6)

    def test_specific_ef_calculation(self):
        """Проверка формулы: EF' = EF + (0.1 - (5-q)*(0.08 + (5-q)*0.02))."""
        # q=4: EF' = 2.5 + (0.1 - 1*(0.08 + 1*0.02)) = 2.5 + 0.0 = 2.5
        self.assertAlmostEqual(calculate_easiness_factor(2.5, 4), 2.5, places=4)
        # q=5: EF' = 2.5 + (0.1 - 0) = 2.6
        self.assertAlmostEqual(calculate_easiness_factor(2.5, 5), 2.6, places=4)
        # q=3: EF' = 2.5 + (0.1 - 2*(0.08 + 2*0.02)) = 2.5 + (0.1 - 0.24) = 2.36
        self.assertAlmostEqual(calculate_easiness_factor(2.5, 3), 2.36, places=4)


class TestCalculateInterval(unittest.TestCase):
    """Тесты расчёта интервалов повторения."""

    def test_first_repetition(self):
        """Первое повторение: интервал = 1 день."""
        self.assertEqual(calculate_interval(1, 2.5, 0), 1)

    def test_second_repetition(self):
        """Второе повторение: интервал = 6 дней."""
        self.assertEqual(calculate_interval(2, 2.5, 1), 6)

    def test_third_repetition(self):
        """Третье повторение: интервал = предыдущий * EF."""
        interval = calculate_interval(3, 2.5, 6)
        self.assertEqual(interval, 15)  # round(6 * 2.5) = 15

    def test_interval_growth(self):
        """Интервалы должны расти с каждым повторением."""
        intervals = []
        interval = 0
        ef = 2.5
        for n in range(1, 7):
            interval = calculate_interval(n, ef, interval)
            intervals.append(interval)
        # Проверяем возрастание (кроме 1→6 скачка)
        for i in range(1, len(intervals)):
            self.assertGreaterEqual(intervals[i], intervals[i-1])

    def test_max_interval_limit(self):
        """Интервал не должен превышать MAX_INTERVAL."""
        interval = calculate_interval(10, 2.5, 500)
        self.assertLessEqual(interval, MAX_INTERVAL)


class TestSM2Algorithm(unittest.TestCase):
    """Тесты основной функции алгоритма SM-2."""

    def test_new_card_perfect_answer(self):
        """Новая карточка с оценкой 5."""
        result = sm2_algorithm(quality=5)
        self.assertEqual(result.repetitions, 1)
        self.assertEqual(result.interval, 1)
        self.assertGreater(result.easiness_factor, DEFAULT_EASINESS_FACTOR)

    def test_new_card_failed_answer(self):
        """Новая карточка с оценкой 0 — сброс."""
        result = sm2_algorithm(quality=0)
        self.assertEqual(result.repetitions, 0)
        self.assertEqual(result.interval, 1)

    def test_reset_on_bad_quality(self):
        """При q < 3 repetitions сбрасывается в 0."""
        for q in [0, 1, 2]:
            result = sm2_algorithm(quality=q, repetitions=5, interval=30)
            self.assertEqual(result.repetitions, 0, f"Failed for quality={q}")
            self.assertEqual(result.interval, 1, f"Failed for quality={q}")

    def test_progress_on_good_quality(self):
        """При q >= 3 repetitions увеличивается."""
        for q in [3, 4, 5]:
            result = sm2_algorithm(quality=q, repetitions=2, interval=6)
            self.assertEqual(result.repetitions, 3, f"Failed for quality={q}")

    def test_next_review_date(self):
        """Дата следующего повторения должна быть корректной."""
        today = date(2025, 6, 1)
        result = sm2_algorithm(quality=5, review_date=today)
        self.assertEqual(result.next_review, today + timedelta(days=1))

    def test_full_learning_cycle(self):
        """Полный цикл обучения: 5 повторений с оценкой 4."""
        rep = 0
        ef = DEFAULT_EASINESS_FACTOR
        interval = 0
        today = date(2025, 1, 1)

        expected_intervals = [1, 6]  # Первые два интервала фиксированы

        for i in range(5):
            result = sm2_algorithm(
                quality=4, repetitions=rep,
                easiness_factor=ef, interval=interval,
                review_date=today,
            )
            rep = result.repetitions
            ef = result.easiness_factor
            interval = result.interval
            today = result.next_review

            if i < 2:
                self.assertEqual(interval, expected_intervals[i],
                    f"Iteration {i}: expected {expected_intervals[i]}, got {interval}")

        # После 5 повторений с q=4 интервал должен быть значительным
        self.assertGreater(interval, 10)
        self.assertEqual(rep, 5)

    def test_ef_preserved_on_reset(self):
        """При сбросе EF изменяется, но не сбрасывается к 2.5."""
        # Сначала учим карточку
        result1 = sm2_algorithm(quality=5, repetitions=3, easiness_factor=2.8, interval=15)
        # Теперь забываем
        result2 = sm2_algorithm(quality=1, repetitions=result1.repetitions,
                                 easiness_factor=result1.easiness_factor,
                                 interval=result1.interval)
        # EF должен измениться, но не стать 2.5
        self.assertNotEqual(result2.easiness_factor, DEFAULT_EASINESS_FACTOR)
        self.assertEqual(result2.repetitions, 0)

    def test_invalid_quality_raises(self):
        """Некорректная оценка вызывает ошибку."""
        with self.assertRaises(ValueError):
            sm2_algorithm(quality=-1)
        with self.assertRaises(ValueError):
            sm2_algorithm(quality=6)

    def test_return_type(self):
        """Результат должен быть SM2Result."""
        result = sm2_algorithm(quality=4)
        self.assertIsInstance(result, SM2Result)
        self.assertIsInstance(result.next_review, date)
        self.assertIsInstance(result.easiness_factor, float)
        self.assertIsInstance(result.interval, int)
        self.assertIsInstance(result.repetitions, int)


class TestSM2EdgeCases(unittest.TestCase):
    """Граничные случаи."""

    def test_many_failures_then_success(self):
        """Многократные неудачи, затем успешное повторение."""
        rep = 0
        ef = DEFAULT_EASINESS_FACTOR
        interval = 0

        # 5 неудач
        for _ in range(5):
            result = sm2_algorithm(quality=1, repetitions=rep,
                                    easiness_factor=ef, interval=interval)
            rep = result.repetitions
            ef = result.easiness_factor
            interval = result.interval

        self.assertEqual(rep, 0)
        self.assertGreaterEqual(ef, MIN_EASINESS_FACTOR)

        # Теперь успех
        result = sm2_algorithm(quality=5, repetitions=rep,
                                easiness_factor=ef, interval=interval)
        self.assertEqual(result.repetitions, 1)
        self.assertEqual(result.interval, 1)

    def test_alternating_quality(self):
        """Чередование хороших и плохих ответов."""
        rep = 0
        ef = DEFAULT_EASINESS_FACTOR
        interval = 0

        qualities = [5, 5, 5, 1, 5, 5, 5]  # Хорошо, потом сброс, потом снова
        for q in qualities:
            result = sm2_algorithm(quality=q, repetitions=rep,
                                    easiness_factor=ef, interval=interval)
            rep = result.repetitions
            ef = result.easiness_factor
            interval = result.interval

        # После последних 3 пятёрок после сброса: rep=3
        self.assertEqual(rep, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
