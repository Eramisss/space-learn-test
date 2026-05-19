"""
REST API веб-приложения для обучения с использованием интервальных повторений.

Стек: Flask + SQLite + JWT-аутентификация + алгоритм SM-2.

Endpoints:
    POST   /api/auth/register       — Регистрация
    POST   /api/auth/login          — Вход (получение JWT)
    GET    /api/auth/me             — Текущий пользователь
    GET    /api/decks               — Список колод
    POST   /api/decks               — Создание колоды
    GET    /api/decks/<id>          — Детали колоды
    PUT    /api/decks/<id>          — Редактирование колоды
    DELETE /api/decks/<id>          — Удаление колоды
    GET    /api/decks/<id>/cards    — Карточки колоды
    POST   /api/decks/<id>/cards    — Создание карточки
    POST   /api/decks/<id>/import   — Импорт карточек (CSV-формат)
    PUT    /api/cards/<id>          — Редактирование карточки
    DELETE /api/cards/<id>          — Удаление карточки
    GET    /api/review/today        — Карточки на повторение сегодня
    POST   /api/review/<card_id>   — Отправка результата повторения
    GET    /api/stats/overview      — Статистика пользователя
"""

import os
import sys
import json
import hashlib
import functools
from datetime import datetime, timedelta, date, timezone

from flask import Flask, request, jsonify, send_from_directory
import jwt as pyjwt

# Добавить путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import (
    init_db, create_user, get_user_by_username, get_user_by_id,
    create_deck, get_decks_by_user, get_deck_by_id, update_deck, delete_deck,
    create_card, get_cards_by_deck, update_card, delete_card, bulk_create_cards,
    get_cards_due_for_review, create_review_log, get_latest_review,
    get_user_stats
)
from sm2 import sm2_algorithm, DEFAULT_EASINESS_FACTOR

# ===================== КОНФИГУРАЦИЯ =====================

app = Flask(__name__, static_folder="../frontend", static_url_path="")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
JWT_EXPIRATION_HOURS = 24

# ===================== УТИЛИТЫ =====================

def hash_password(password: str) -> str:
    """Хеширование пароля с использованием SHA-256 + salt."""
    salt = "spaced-repetition-salt"  # В production использовать bcrypt
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def create_token(user_id: str) -> str:
    """Создать JWT-токен."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Декодировать JWT-токен."""
    return pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])


def auth_required(f):
    """Декоратор для проверки JWT-аутентификации."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Требуется авторизация"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
            user = get_user_by_id(payload["user_id"])
            if not user:
                return jsonify({"error": "Пользователь не найден"}), 401
            request.current_user = user
        except pyjwt.ExpiredSignatureError:
            return jsonify({"error": "Токен истёк"}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"error": "Невалидный токен"}), 401
        return f(*args, **kwargs)
    return decorated


# ===================== МАРШРУТЫ: АУТЕНТИФИКАЦИЯ =====================

@app.route("/api/auth/register", methods=["POST"])
def register():
    """Регистрация нового пользователя."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Требуется JSON body"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    # Валидация
    errors = []
    if len(username) < 3:
        errors.append("Имя пользователя — минимум 3 символа")
    if "@" not in email or "." not in email:
        errors.append("Некорректный email")
    if len(password) < 6:
        errors.append("Пароль — минимум 6 символов")
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    # Проверка уникальности
    if get_user_by_username(username):
        return jsonify({"error": "Имя пользователя уже занято"}), 409

    try:
        user = create_user(username, email, hash_password(password))
        token = create_token(user["id"])
        return jsonify({"user": user, "token": token}), 201
    except Exception as e:
        return jsonify({"error": f"Ошибка регистрации: {str(e)}"}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Аутентификация пользователя."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Требуется JSON body"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = get_user_by_username(username)
    if not user or user["password_hash"] != hash_password(password):
        return jsonify({"error": "Неверное имя пользователя или пароль"}), 401

    token = create_token(user["id"])
    return jsonify({
        "user": {"id": user["id"], "username": user["username"], "email": user["email"]},
        "token": token,
    })


@app.route("/api/auth/me", methods=["GET"])
@auth_required
def get_me():
    """Получить данные текущего пользователя."""
    user = request.current_user
    return jsonify({
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
    })


# ===================== МАРШРУТЫ: КОЛОДЫ =====================

@app.route("/api/decks", methods=["GET"])
@auth_required
def list_decks():
    """Получить список колод текущего пользователя."""
    decks = get_decks_by_user(request.current_user["id"])
    return jsonify(decks)


@app.route("/api/decks", methods=["POST"])
@auth_required
def create_deck_route():
    """Создать новую колоду."""
    data = request.get_json()
    if not data or not data.get("title", "").strip():
        return jsonify({"error": "Укажите название колоды"}), 400

    deck = create_deck(
        owner_id=request.current_user["id"],
        title=data["title"].strip(),
        description=data.get("description", ""),
        is_public=data.get("is_public", False),
    )
    return jsonify(deck), 201


@app.route("/api/decks/<deck_id>", methods=["GET"])
@auth_required
def get_deck_route(deck_id):
    """Получить информацию о колоде."""
    deck = get_deck_by_id(deck_id)
    if not deck:
        return jsonify({"error": "Колода не найдена"}), 404
    if deck["owner_id"] != request.current_user["id"] and not deck["is_public"]:
        return jsonify({"error": "Доступ запрещён"}), 403
    return jsonify(deck)


@app.route("/api/decks/<deck_id>", methods=["PUT"])
@auth_required
def update_deck_route(deck_id):
    """Обновить колоду."""
    deck = get_deck_by_id(deck_id)
    if not deck:
        return jsonify({"error": "Колода не найдена"}), 404
    if deck["owner_id"] != request.current_user["id"]:
        return jsonify({"error": "Доступ запрещён"}), 403

    data = request.get_json()
    update_deck(
        deck_id,
        title=data.get("title", deck["title"]),
        description=data.get("description", deck["description"]),
        is_public=data.get("is_public", deck["is_public"]),
    )
    return jsonify({"message": "Колода обновлена"})


@app.route("/api/decks/<deck_id>", methods=["DELETE"])
@auth_required
def delete_deck_route(deck_id):
    """Удалить колоду."""
    deck = get_deck_by_id(deck_id)
    if not deck:
        return jsonify({"error": "Колода не найдена"}), 404
    if deck["owner_id"] != request.current_user["id"]:
        return jsonify({"error": "Доступ запрещён"}), 403
    delete_deck(deck_id)
    return jsonify({"message": "Колода удалена"})


# ===================== МАРШРУТЫ: КАРТОЧКИ =====================

@app.route("/api/decks/<deck_id>/cards", methods=["GET"])
@auth_required
def list_cards(deck_id):
    """Получить карточки колоды."""
    deck = get_deck_by_id(deck_id)
    if not deck:
        return jsonify({"error": "Колода не найдена"}), 404
    cards = get_cards_by_deck(deck_id)
    return jsonify(cards)


@app.route("/api/decks/<deck_id>/cards", methods=["POST"])
@auth_required
def create_card_route(deck_id):
    """Создать карточку в колоде."""
    deck = get_deck_by_id(deck_id)
    if not deck:
        return jsonify({"error": "Колода не найдена"}), 404
    if deck["owner_id"] != request.current_user["id"]:
        return jsonify({"error": "Доступ запрещён"}), 403

    data = request.get_json()
    front = data.get("front", "").strip()
    back = data.get("back", "").strip()
    if not front or not back:
        return jsonify({"error": "Заполните обе стороны карточки"}), 400

    card = create_card(deck_id, front, back)
    return jsonify(card), 201


@app.route("/api/decks/<deck_id>/import", methods=["POST"])
@auth_required
def import_cards(deck_id):
    """Импорт карточек (JSON массив [{front, back}, ...])."""
    deck = get_deck_by_id(deck_id)
    if not deck:
        return jsonify({"error": "Колода не найдена"}), 404
    if deck["owner_id"] != request.current_user["id"]:
        return jsonify({"error": "Доступ запрещён"}), 403

    data = request.get_json()
    cards_data = data.get("cards", [])
    if not cards_data:
        return jsonify({"error": "Нет карточек для импорта"}), 400

    # Валидация
    valid = []
    for item in cards_data:
        front = item.get("front", "").strip()
        back = item.get("back", "").strip()
        if front and back:
            valid.append({"front": front, "back": back})

    created = bulk_create_cards(deck_id, valid)
    return jsonify({"imported": len(created), "cards": created}), 201


@app.route("/api/cards/<card_id>", methods=["PUT"])
@auth_required
def update_card_route(card_id):
    """Обновить карточку."""
    data = request.get_json()
    front = data.get("front", "").strip()
    back = data.get("back", "").strip()
    if not front or not back:
        return jsonify({"error": "Заполните обе стороны карточки"}), 400
    update_card(card_id, front, back)
    return jsonify({"message": "Карточка обновлена"})


@app.route("/api/cards/<card_id>", methods=["DELETE"])
@auth_required
def delete_card_route(card_id):
    """Удалить карточку."""
    delete_card(card_id)
    return jsonify({"message": "Карточка удалена"})


# ===================== МАРШРУТЫ: ПОВТОРЕНИЕ =====================

@app.route("/api/review/today", methods=["GET"])
@auth_required
def get_review_today():
    """Получить карточки для повторения сегодня."""
    deck_id = request.args.get("deck_id")
    cards = get_cards_due_for_review(request.current_user["id"], deck_id)
    return jsonify(cards)


@app.route("/api/review/<card_id>", methods=["POST"])
@auth_required
def submit_review(card_id):
    """
    Отправить результат повторения карточки.

    Body: {"quality": 0-5}

    Выполняет:
    1. Получает текущие параметры карточки
    2. Вызывает алгоритм SM-2
    3. Сохраняет результат в review_logs
    """
    data = request.get_json()
    quality = data.get("quality")
    if quality is None or not (0 <= quality <= 5):
        return jsonify({"error": "Оценка качества должна быть от 0 до 5"}), 400

    user_id = request.current_user["id"]

    # Получить текущие параметры
    latest = get_latest_review(user_id, card_id)
    if latest:
        repetitions = latest["repetitions"]
        ef = latest["easiness_factor"]
        interval = latest["interval_days"]
    else:
        repetitions = 0
        ef = DEFAULT_EASINESS_FACTOR
        interval = 0

    # Вычислить новые параметры по SM-2
    result = sm2_algorithm(
        quality=quality,
        repetitions=repetitions,
        easiness_factor=ef,
        interval=interval,
    )

    # Сохранить запись повторения
    log = create_review_log(
        user_id=user_id,
        card_id=card_id,
        quality=quality,
        easiness_factor=result.easiness_factor,
        interval_days=result.interval,
        repetitions=result.repetitions,
        next_review=result.next_review,
    )

    return jsonify({
        "review": log,
        "sm2_result": {
            "repetitions": result.repetitions,
            "easiness_factor": result.easiness_factor,
            "interval": result.interval,
            "next_review": result.next_review.isoformat(),
        },
    })


# ===================== МАРШРУТЫ: СТАТИСТИКА =====================

@app.route("/api/stats/overview", methods=["GET"])
@auth_required
def get_stats():
    """Получить статистику пользователя."""
    stats = get_user_stats(request.current_user["id"])
    return jsonify(stats)


# ===================== ФРОНТЕНД =====================

@app.route("/")
def serve_frontend():
    """Отдать фронтенд SPA."""
    return send_from_directory(app.static_folder, "index.html")


# ===================== CORS =====================

@app.after_request
def after_request(response):
    """Добавить CORS-заголовки."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


# ===================== ЗАПУСК =====================

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    init_db()
    print("=" * 60)
    print("  Веб-приложение интервальных повторений")
    print("  Запуск: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
