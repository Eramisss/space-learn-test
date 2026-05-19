"""
Модуль работы с базой данных SQLite.

Содержит функции инициализации схемы БД, а также CRUD-операции
для сущностей: User, Deck, Card, ReviewLog.

Структура таблиц соответствует ER-диаграмме проекта.
"""

import sqlite3
import uuid
from datetime import date, datetime
from typing import Optional
from contextlib import contextmanager

DATABASE_PATH = "spaced_repetition.db"


@contextmanager
def get_db():
    """Контекстный менеджер для подключения к БД."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Инициализация схемы базы данных."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                date_joined TEXT NOT NULL DEFAULT (datetime('now')),
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS decks (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                is_public INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                deck_id TEXT NOT NULL,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS review_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                card_id TEXT NOT NULL,
                quality INTEGER NOT NULL CHECK (quality >= 0 AND quality <= 5),
                easiness_factor REAL NOT NULL CHECK (easiness_factor >= 1.3),
                interval_days INTEGER NOT NULL,
                repetitions INTEGER NOT NULL DEFAULT 0,
                next_review TEXT NOT NULL,
                reviewed_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_review_logs_user_card
                ON review_logs(user_id, card_id);
            CREATE INDEX IF NOT EXISTS idx_review_logs_next_review
                ON review_logs(user_id, next_review);
            CREATE INDEX IF NOT EXISTS idx_decks_owner
                ON decks(owner_id);
            CREATE INDEX IF NOT EXISTS idx_cards_deck
                ON cards(deck_id);
        """)


def generate_id() -> str:
    """Генерация UUID."""
    return str(uuid.uuid4())


# ===================== USER OPERATIONS =====================

def create_user(username: str, email: str, password_hash: str) -> dict:
    """Создать нового пользователя."""
    user_id = generate_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, username, email, password_hash)
        )
    return {"id": user_id, "username": username, "email": email}


def get_user_by_username(username: str) -> Optional[dict]:
    """Получить пользователя по имени."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Получить пользователя по ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


# ===================== DECK OPERATIONS =====================

def create_deck(owner_id: str, title: str, description: str = "",
                is_public: bool = False) -> dict:
    """Создать новую колоду."""
    deck_id = generate_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO decks (id, owner_id, title, description, is_public)
               VALUES (?, ?, ?, ?, ?)""",
            (deck_id, owner_id, title, description, int(is_public))
        )
    return {"id": deck_id, "owner_id": owner_id, "title": title,
            "description": description, "is_public": is_public}


def get_decks_by_user(user_id: str) -> list:
    """Получить все колоды пользователя с количеством карточек."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT d.*,
                   COUNT(c.id) as card_count,
                   SUM(CASE WHEN rl.next_review IS NOT NULL
                        AND rl.next_review <= ? THEN 1 ELSE 0 END) as due_count
            FROM decks d
            LEFT JOIN cards c ON c.deck_id = d.id
            LEFT JOIN (
                SELECT card_id, next_review,
                       ROW_NUMBER() OVER (PARTITION BY card_id ORDER BY reviewed_at DESC) as rn
                FROM review_logs WHERE user_id = ?
            ) rl ON rl.card_id = c.id AND rl.rn = 1
            WHERE d.owner_id = ?
            GROUP BY d.id
            ORDER BY d.updated_at DESC
        """, (date.today().isoformat(), user_id, user_id)).fetchall()
    return [dict(r) for r in rows]


def get_deck_by_id(deck_id: str) -> Optional[dict]:
    """Получить колоду по ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)).fetchone()
    return dict(row) if row else None


def update_deck(deck_id: str, title: str, description: str,
                is_public: bool) -> bool:
    """Обновить колоду."""
    with get_db() as conn:
        result = conn.execute(
            """UPDATE decks SET title = ?, description = ?, is_public = ?,
               updated_at = datetime('now') WHERE id = ?""",
            (title, description, int(is_public), deck_id)
        )
    return result.rowcount > 0


def delete_deck(deck_id: str) -> bool:
    """Удалить колоду."""
    with get_db() as conn:
        result = conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
    return result.rowcount > 0


# ===================== CARD OPERATIONS =====================

def create_card(deck_id: str, front: str, back: str) -> dict:
    """Создать карточку."""
    card_id = generate_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO cards (id, deck_id, front, back) VALUES (?, ?, ?, ?)",
            (card_id, deck_id, front, back)
        )
        # Обновить updated_at у колоды
        conn.execute(
            "UPDATE decks SET updated_at = datetime('now') WHERE id = ?",
            (deck_id,)
        )
    return {"id": card_id, "deck_id": deck_id, "front": front, "back": back}


def get_cards_by_deck(deck_id: str) -> list:
    """Получить все карточки колоды."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM cards WHERE deck_id = ? ORDER BY created_at",
            (deck_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def update_card(card_id: str, front: str, back: str) -> bool:
    """Обновить карточку."""
    with get_db() as conn:
        result = conn.execute(
            "UPDATE cards SET front = ?, back = ? WHERE id = ?",
            (front, back, card_id)
        )
    return result.rowcount > 0


def delete_card(card_id: str) -> bool:
    """Удалить карточку."""
    with get_db() as conn:
        result = conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    return result.rowcount > 0


def bulk_create_cards(deck_id: str, cards_data: list) -> list:
    """Массовое создание карточек (импорт из CSV)."""
    created = []
    with get_db() as conn:
        for item in cards_data:
            card_id = generate_id()
            conn.execute(
                "INSERT INTO cards (id, deck_id, front, back) VALUES (?, ?, ?, ?)",
                (card_id, deck_id, item["front"], item["back"])
            )
            created.append({"id": card_id, "front": item["front"], "back": item["back"]})
        conn.execute(
            "UPDATE decks SET updated_at = datetime('now') WHERE id = ?",
            (deck_id,)
        )
    return created


# ===================== REVIEW OPERATIONS =====================

def get_cards_due_for_review(user_id: str, deck_id: Optional[str] = None,
                              new_cards_limit: int = 20) -> list:
    """
    Получить карточки для повторения сегодня.

    Включает:
    1. Карточки, у которых next_review <= сегодня
    2. Новые карточки (без записей повторений), до new_cards_limit штук
    """
    today = date.today().isoformat()
    with get_db() as conn:
        # Карточки с просроченным повторением
        deck_filter = "AND c.deck_id = ?" if deck_id else ""
        params_due = [user_id, today, user_id]
        params_new = [user_id]
        if deck_id:
            params_due.append(deck_id)
            params_new.append(deck_id)

        due_cards = conn.execute(f"""
            SELECT c.*, rl.easiness_factor, rl.interval_days,
                   rl.repetitions, rl.next_review
            FROM cards c
            JOIN (
                SELECT card_id, easiness_factor, interval_days, repetitions,
                       next_review,
                       ROW_NUMBER() OVER (PARTITION BY card_id ORDER BY reviewed_at DESC) as rn
                FROM review_logs WHERE user_id = ?
            ) rl ON rl.card_id = c.id AND rl.rn = 1
            WHERE rl.next_review <= ?
            AND c.id IN (SELECT card_id FROM review_logs WHERE user_id = ?)
            {deck_filter}
            ORDER BY rl.easiness_factor ASC
        """, params_due).fetchall()

        # Новые карточки (без записей повторений)
        new_cards = conn.execute(f"""
            SELECT c.*, NULL as easiness_factor, NULL as interval_days,
                   NULL as repetitions, NULL as next_review
            FROM cards c
            WHERE c.id NOT IN (
                SELECT card_id FROM review_logs WHERE user_id = ?
            )
            {deck_filter}
            ORDER BY c.created_at
            LIMIT ?
        """, params_new + [new_cards_limit]).fetchall()

    return [dict(r) for r in due_cards] + [dict(r) for r in new_cards]


def create_review_log(user_id: str, card_id: str, quality: int,
                      easiness_factor: float, interval_days: int,
                      repetitions: int, next_review: date) -> dict:
    """Создать запись повторения."""
    log_id = generate_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO review_logs
               (id, user_id, card_id, quality, easiness_factor,
                interval_days, repetitions, next_review)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (log_id, user_id, card_id, quality, easiness_factor,
             interval_days, repetitions, next_review.isoformat())
        )
    return {"id": log_id, "quality": quality, "next_review": next_review.isoformat()}


def get_latest_review(user_id: str, card_id: str) -> Optional[dict]:
    """Получить последнюю запись повторения для карточки."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM review_logs
               WHERE user_id = ? AND card_id = ?
               ORDER BY reviewed_at DESC LIMIT 1""",
            (user_id, card_id)
        ).fetchone()
    return dict(row) if row else None


# ===================== STATS OPERATIONS =====================

def get_user_stats(user_id: str) -> dict:
    """Получить общую статистику пользователя."""
    with get_db() as conn:
        # Общее количество карточек
        total = conn.execute("""
            SELECT COUNT(*) as cnt FROM cards c
            JOIN decks d ON c.deck_id = d.id
            WHERE d.owner_id = ?
        """, (user_id,)).fetchone()["cnt"]

        # Карточки с записями повторений
        reviewed = conn.execute("""
            SELECT COUNT(DISTINCT card_id) as cnt
            FROM review_logs WHERE user_id = ?
        """, (user_id,)).fetchone()["cnt"]

        # Карточки на повторении сегодня
        due_today = conn.execute("""
            SELECT COUNT(*) as cnt FROM (
                SELECT card_id,
                       ROW_NUMBER() OVER (PARTITION BY card_id ORDER BY reviewed_at DESC) as rn,
                       next_review
                FROM review_logs WHERE user_id = ?
            ) WHERE rn = 1 AND next_review <= ?
        """, (user_id, date.today().isoformat())).fetchone()["cnt"]

        # Средний EF
        avg_ef = conn.execute("""
            SELECT AVG(easiness_factor) as avg_ef FROM (
                SELECT easiness_factor,
                       ROW_NUMBER() OVER (PARTITION BY card_id ORDER BY reviewed_at DESC) as rn
                FROM review_logs WHERE user_id = ?
            ) WHERE rn = 1
        """, (user_id,)).fetchone()["avg_ef"]

        # История повторений по дням (последние 30 дней)
        history = conn.execute("""
            SELECT DATE(reviewed_at) as day,
                   COUNT(*) as review_count,
                   ROUND(AVG(quality), 2) as avg_quality
            FROM review_logs
            WHERE user_id = ?
            AND reviewed_at >= date('now', '-30 days')
            GROUP BY DATE(reviewed_at)
            ORDER BY day
        """, (user_id,)).fetchall()

    return {
        "total_cards": total,
        "reviewed_cards": reviewed,
        "new_cards": total - reviewed,
        "due_today": due_today,
        "average_ef": round(avg_ef, 2) if avg_ef else 2.5,
        "daily_history": [dict(r) for r in history],
    }
