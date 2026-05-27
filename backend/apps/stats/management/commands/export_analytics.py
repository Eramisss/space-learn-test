"""
Management-команда выгрузки данных апробации для анализа в ВКР.

Использование:
    python manage.py export_analytics                 # выгрузка в ./exports/
    python manage.py export_analytics --out /tmp/data # в указанную папку

Генерирует:
    users.csv     — сводка по пользователям (регистрация, активность, точность)
    reviews.csv   — полный лог повторений (для графиков и статистики)
    cards.csv     — текущее состояние всех карточек (EF, интервал, n)
    summary.txt   — агрегированные показатели одной строкой
"""

import csv
import os
from datetime import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Max, Min, Q

from apps.cards.models import Card
from apps.decks.models import Deck
from apps.reviews.models import ReviewLog


class Command(BaseCommand):
    help = 'Выгружает агрегированные данные пользователей и журнал повторений в CSV для анализа апробации.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--out',
            default='exports',
            help='Каталог для CSV-файлов (по умолчанию ./exports/)',
        )
        parser.add_argument(
            '--exclude-staff',
            action='store_true',
            help='Не включать суперпользователей и админов в выгрузку.',
        )

    def handle(self, *args, **opts):
        out_dir = opts['out']
        os.makedirs(out_dir, exist_ok=True)

        users_qs = User.objects.all()
        if opts['exclude_staff']:
            users_qs = users_qs.filter(is_staff=False, is_superuser=False)

        user_ids = list(users_qs.values_list('id', flat=True))

        self._export_users(out_dir, users_qs)
        self._export_reviews(out_dir, user_ids)
        self._export_cards(out_dir, user_ids)
        self._export_summary(out_dir, users_qs, user_ids)

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Файлы сохранены в {os.path.abspath(out_dir)}'
        ))

    # ------------------------------------------------------------------

    def _export_users(self, out_dir, users_qs):
        """Сводка по каждому пользователю — одна строка на участника."""
        path = os.path.join(out_dir, 'users.csv')
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow([
                'user_id', 'username', 'date_joined',
                'decks_count', 'cards_count', 'reviews_count',
                'first_review', 'last_review',
                'avg_quality', 'recall_rate', 'avg_ef',
            ])
            for u in users_qs:
                decks = Deck.objects.filter(owner=u).count()
                cards = Card.objects.filter(deck__owner=u).count()
                rev = ReviewLog.objects.filter(user=u)
                rev_count = rev.count()

                agg = rev.aggregate(
                    first=Min('reviewed_at'),
                    last=Max('reviewed_at'),
                    avg_q=Avg('quality'),
                    avg_ef=Avg('easiness_factor'),
                    success=Count('id', filter=Q(quality__gte=3)),
                )
                recall = (agg['success'] / rev_count) if rev_count else 0.0

                w.writerow([
                    u.id, u.username, u.date_joined.isoformat(),
                    decks, cards, rev_count,
                    agg['first'].isoformat() if agg['first'] else '',
                    agg['last'].isoformat() if agg['last'] else '',
                    f"{agg['avg_q']:.3f}" if agg['avg_q'] is not None else '',
                    f'{recall:.3f}',
                    f"{agg['avg_ef']:.3f}" if agg['avg_ef'] is not None else '',
                ])
        self.stdout.write(f'  + users.csv ({users_qs.count()} строк)')

    def _export_reviews(self, out_dir, user_ids):
        """Полный журнал повторений — основная таблица для анализа."""
        path = os.path.join(out_dir, 'reviews.csv')
        qs = ReviewLog.objects.filter(user_id__in=user_ids).select_related(
            'card', 'card__deck'
        ).order_by('reviewed_at')

        count = 0
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow([
                'review_id', 'user_id', 'card_id', 'deck_id', 'deck_title',
                'quality', 'easiness_factor', 'interval_days', 'repetitions',
                'reviewed_at', 'next_review',
            ])
            for r in qs.iterator(chunk_size=2000):
                w.writerow([
                    r.id, r.user_id, r.card_id,
                    r.card.deck_id, r.card.deck.title,
                    r.quality, f'{r.easiness_factor:.4f}',
                    r.interval_days, r.repetitions,
                    r.reviewed_at.isoformat(),
                    r.next_review.isoformat(),
                ])
                count += 1
        self.stdout.write(f'  + reviews.csv ({count} строк)')

    def _export_cards(self, out_dir, user_ids):
        """Текущее состояние карточек: последний EF, интервал, число повторений."""
        path = os.path.join(out_dir, 'cards.csv')
        qs = Card.objects.filter(deck__owner_id__in=user_ids).select_related('deck')

        count = 0
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow([
                'card_id', 'deck_id', 'deck_title', 'owner_id',
                'front', 'created_at',
                'reviews_count', 'last_quality', 'last_ef',
                'last_interval', 'last_repetitions', 'next_review',
            ])
            for c in qs.iterator(chunk_size=1000):
                last = ReviewLog.objects.filter(card=c).order_by('-reviewed_at').first()
                rev_count = ReviewLog.objects.filter(card=c).count()
                w.writerow([
                    c.id, c.deck_id, c.deck.title, c.deck.owner_id,
                    c.front[:80], c.created_at.isoformat(),
                    rev_count,
                    last.quality if last else '',
                    f'{last.easiness_factor:.4f}' if last else '',
                    last.interval_days if last else '',
                    last.repetitions if last else '',
                    last.next_review.isoformat() if last else '',
                ])
                count += 1
        self.stdout.write(f'  + cards.csv ({count} строк)')

    def _export_summary(self, out_dir, users_qs, user_ids):
        """Текстовый сводный отчёт — готовые числа для раздела «Апробация»."""
        path = os.path.join(out_dir, 'summary.txt')

        users_total = users_qs.count()
        users_active = users_qs.filter(reviews__isnull=False).distinct().count()
        decks_total = Deck.objects.filter(owner_id__in=user_ids).count()
        cards_total = Card.objects.filter(deck__owner_id__in=user_ids).count()
        reviews_total = ReviewLog.objects.filter(user_id__in=user_ids).count()

        agg = ReviewLog.objects.filter(user_id__in=user_ids).aggregate(
            avg_q=Avg('quality'),
            avg_ef=Avg('easiness_factor'),
            success=Count('id', filter=Q(quality__gte=3)),
            first=Min('reviewed_at'),
            last=Max('reviewed_at'),
        )
        recall = (agg['success'] / reviews_total) if reviews_total else 0.0

        with open(path, 'w', encoding='utf-8') as f:
            f.write('Сводный отчёт апробации\n')
            f.write(f'Сформирован: {datetime.now().isoformat(timespec="seconds")}\n')
            f.write('=' * 50 + '\n\n')
            f.write(f'Пользователи всего:       {users_total}\n')
            f.write(f'Активные (≥1 повторение): {users_active}\n')
            f.write(f'Колоды всего:             {decks_total}\n')
            f.write(f'Карточки всего:           {cards_total}\n')
            f.write(f'Повторения всего:         {reviews_total}\n')
            f.write('\n')
            if reviews_total:
                f.write(f'Средняя оценка качества:  {agg["avg_q"]:.3f} / 5\n')
                f.write(f'Доля успешных (q≥3):      {recall:.1%}\n')
                f.write(f'Средний EF:               {agg["avg_ef"]:.3f}\n')
                f.write(f'Период наблюдений:        {agg["first"].date()} … {agg["last"].date()}\n')
        self.stdout.write('  + summary.txt')
