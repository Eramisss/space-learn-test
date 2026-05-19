"""
Модуль реализации алгоритма интервальных повторений SM-2.

Алгоритм SM-2 разработан Петром Возняком (1987).
Используется для расчёта оптимальных интервалов повторения
на основе оценки качества ответа пользователя.

Параметры карточки:
    - repetitions (n): количество успешных повторений подряд
    - easiness_factor (EF): коэффициент лёгкости (≥ 1.3, начальное 2.5)
    - interval: текущий интервал в днях до следующего повторения
    - quality (q): оценка качества ответа (0–5)

Формула пересчёта EF:
    EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))

Формулы расчёта интервалов:
    I(1) = 1 день
    I(2) = 6 дней
    I(n) = I(n-1) * EF, для n > 2

Если q < 3: repetitions сбрасывается в 0, interval = 1.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


# Минимальное значение коэффициента лёгкости
MIN_EASINESS_FACTOR = 1.3

# Начальное значение коэффициента лёгкости
DEFAULT_EASINESS_FACTOR = 2.5

# Максимальный интервал повторения (дни)
MAX_INTERVAL = 365


@dataclass
class SM2Result:
    """Результат вычисления алгоритма SM-2."""
    repetitions: int
    easiness_factor: float
    interval: int
    next_review: date


def calculate_easiness_factor(ef: float, quality: int) -> float:
    """
    Пересчитать коэффициент лёгкости (EF) на основе оценки качества.

    Args:
        ef: текущий коэффициент лёгкости (≥ 1.3)
        quality: оценка качества ответа (0–5)

    Returns:
        Обновлённый коэффициент лёгкости (не менее MIN_EASINESS_FACTOR)
    """
    if not 0 <= quality <= 5:
        raise ValueError(f"Оценка качества должна быть от 0 до 5, получено: {quality}")

    new_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return max(new_ef, MIN_EASINESS_FACTOR)


def calculate_interval(repetitions: int, easiness_factor: float,
                       previous_interval: int) -> int:
    """
    Рассчитать интервал до следующего повторения.

    Args:
        repetitions: номер текущего успешного повторения (начиная с 1)
        easiness_factor: коэффициент лёгкости карточки
        previous_interval: предыдущий интервал в днях

    Returns:
        Новый интервал в днях
    """
    if repetitions == 1:
        return 1
    elif repetitions == 2:
        return 6
    else:
        new_interval = round(previous_interval * easiness_factor)
        return min(new_interval, MAX_INTERVAL)


def sm2_algorithm(quality: int,
                  repetitions: int = 0,
                  easiness_factor: float = DEFAULT_EASINESS_FACTOR,
                  interval: int = 0,
                  review_date: Optional[date] = None) -> SM2Result:
    """
    Основная функция алгоритма SM-2.

    Вычисляет новые параметры повторения карточки на основе
    оценки качества ответа пользователя.

    Args:
        quality: оценка качества ответа (0–5):
            5 — отлично (мгновенный ответ без колебаний)
            4 — хорошо (правильный ответ после раздумья)
            3 — удовлетворительно (правильный, но с затруднениями)
            2 — неудовлетворительно (неверный, но вспомнил при подсказке)
            1 — плохо (неверный, правильный показался знакомым)
            0 — полное забывание
        repetitions: текущее количество успешных повторений
        easiness_factor: текущий коэффициент лёгкости
        interval: текущий интервал (дни)
        review_date: дата повторения (по умолчанию — сегодня)

    Returns:
        SM2Result с обновлёнными параметрами

    Raises:
        ValueError: если quality не в диапазоне 0–5
    """
    if not 0 <= quality <= 5:
        raise ValueError(f"Оценка качества должна быть от 0 до 5, получено: {quality}")

    if review_date is None:
        review_date = date.today()

    # Пересчитать коэффициент лёгкости
    new_ef = calculate_easiness_factor(easiness_factor, quality)

    if quality < 3:
        # Ответ неудовлетворительный — сброс прогресса
        new_repetitions = 0
        new_interval = 1
    else:
        # Ответ удовлетворительный — продвижение
        new_repetitions = repetitions + 1
        new_interval = calculate_interval(new_repetitions, new_ef, interval)

    next_review = review_date + timedelta(days=new_interval)

    return SM2Result(
        repetitions=new_repetitions,
        easiness_factor=round(new_ef, 4),
        interval=new_interval,
        next_review=next_review,
    )
