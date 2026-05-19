"""
Интеграционные тесты REST API.

Тестируется:
1. Регистрация и аутентификация
2. CRUD операции с колодами
3. CRUD операции с карточками
4. Процесс повторения (review)
5. Статистика
6. Импорт карточек
7. Авторизация и контроль доступа
"""

import sys
import os
import json
import unittest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Перенастроить БД на временный файл до импорта app
import database
database.DATABASE_PATH = tempfile.mktemp(suffix=".db")

from app import app
from database import init_db


class BaseTestCase(unittest.TestCase):
    """Базовый класс для тестов API."""

    def setUp(self):
        """Настройка тестовой среды."""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        # Пересоздать БД
        database.DATABASE_PATH = tempfile.mktemp(suffix=".db")
        init_db()

    def register_user(self, username="testuser", email="test@example.com",
                      password="password123"):
        """Вспомогательный метод: регистрация пользователя."""
        return self.client.post("/api/auth/register",
            data=json.dumps({"username": username, "email": email, "password": password}),
            content_type="application/json")

    def login_user(self, username="testuser", password="password123"):
        """Вспомогательный метод: вход пользователя."""
        return self.client.post("/api/auth/login",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json")

    def get_token(self, username="testuser", email="test@example.com",
                  password="password123"):
        """Вспомогательный метод: получить JWT-токен."""
        self.register_user(username, email, password)
        res = self.login_user(username, password)
        return json.loads(res.data)["token"]

    def auth_headers(self, token=None):
        """Заголовки с JWT."""
        if token is None:
            token = self.get_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestAuth(BaseTestCase):
    """Тесты аутентификации."""

    def test_register_success(self):
        """Успешная регистрация."""
        res = self.register_user()
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertIn("token", data)
        self.assertEqual(data["user"]["username"], "testuser")

    def test_register_duplicate_username(self):
        """Регистрация с занятым именем."""
        self.register_user()
        res = self.register_user()
        self.assertEqual(res.status_code, 409)

    def test_register_short_password(self):
        """Регистрация со слишком коротким паролем."""
        res = self.register_user(password="123")
        self.assertEqual(res.status_code, 400)

    def test_login_success(self):
        """Успешный вход."""
        self.register_user()
        res = self.login_user()
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("token", data)

    def test_login_wrong_password(self):
        """Вход с неверным паролем."""
        self.register_user()
        res = self.login_user(password="wrong")
        self.assertEqual(res.status_code, 401)

    def test_protected_endpoint_without_token(self):
        """Доступ без токена запрещён."""
        res = self.client.get("/api/decks")
        self.assertEqual(res.status_code, 401)

    def test_me_endpoint(self):
        """Получение данных текущего пользователя."""
        token = self.get_token()
        res = self.client.get("/api/auth/me", headers=self.auth_headers(token))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["username"], "testuser")


class TestDecks(BaseTestCase):
    """Тесты CRUD колод."""

    def test_create_deck(self):
        """Создание колоды."""
        headers = self.auth_headers()
        res = self.client.post("/api/decks",
            data=json.dumps({"title": "Тест", "description": "Тестовая колода"}),
            headers=headers)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertEqual(data["title"], "Тест")

    def test_list_decks(self):
        """Список колод."""
        headers = self.auth_headers()
        self.client.post("/api/decks",
            data=json.dumps({"title": "Колода 1"}), headers=headers)
        self.client.post("/api/decks",
            data=json.dumps({"title": "Колода 2"}), headers=headers)
        res = self.client.get("/api/decks", headers=headers)
        data = json.loads(res.data)
        self.assertEqual(len(data), 2)

    def test_delete_deck(self):
        """Удаление колоды."""
        headers = self.auth_headers()
        res = self.client.post("/api/decks",
            data=json.dumps({"title": "Удали меня"}), headers=headers)
        deck_id = json.loads(res.data)["id"]
        res = self.client.delete(f"/api/decks/{deck_id}", headers=headers)
        self.assertEqual(res.status_code, 200)
        # Проверяем, что колода удалена
        res = self.client.get("/api/decks", headers=headers)
        self.assertEqual(len(json.loads(res.data)), 0)

    def test_create_deck_empty_title(self):
        """Создание колоды без названия — ошибка."""
        headers = self.auth_headers()
        res = self.client.post("/api/decks",
            data=json.dumps({"title": ""}), headers=headers)
        self.assertEqual(res.status_code, 400)


class TestCards(BaseTestCase):
    """Тесты CRUD карточек."""

    def _create_deck(self, headers):
        res = self.client.post("/api/decks",
            data=json.dumps({"title": "Тест"}), headers=headers)
        return json.loads(res.data)["id"]

    def test_create_card(self):
        """Создание карточки."""
        headers = self.auth_headers()
        deck_id = self._create_deck(headers)
        res = self.client.post(f"/api/decks/{deck_id}/cards",
            data=json.dumps({"front": "Вопрос", "back": "Ответ"}),
            headers=headers)
        self.assertEqual(res.status_code, 201)

    def test_list_cards(self):
        """Список карточек колоды."""
        headers = self.auth_headers()
        deck_id = self._create_deck(headers)
        for i in range(3):
            self.client.post(f"/api/decks/{deck_id}/cards",
                data=json.dumps({"front": f"Q{i}", "back": f"A{i}"}),
                headers=headers)
        res = self.client.get(f"/api/decks/{deck_id}/cards", headers=headers)
        self.assertEqual(len(json.loads(res.data)), 3)

    def test_delete_card(self):
        """Удаление карточки."""
        headers = self.auth_headers()
        deck_id = self._create_deck(headers)
        res = self.client.post(f"/api/decks/{deck_id}/cards",
            data=json.dumps({"front": "Q", "back": "A"}), headers=headers)
        card_id = json.loads(res.data)["id"]
        res = self.client.delete(f"/api/cards/{card_id}", headers=headers)
        self.assertEqual(res.status_code, 200)

    def test_import_cards(self):
        """Импорт карточек."""
        headers = self.auth_headers()
        deck_id = self._create_deck(headers)
        cards = [
            {"front": "HTML", "back": "HyperText Markup Language"},
            {"front": "CSS", "back": "Cascading Style Sheets"},
            {"front": "JS", "back": "JavaScript"},
        ]
        res = self.client.post(f"/api/decks/{deck_id}/import",
            data=json.dumps({"cards": cards}), headers=headers)
        data = json.loads(res.data)
        self.assertEqual(data["imported"], 3)


class TestReview(BaseTestCase):
    """Тесты процесса повторения."""

    def _setup_deck_with_cards(self, headers, n=3):
        """Создать колоду с n карточками."""
        res = self.client.post("/api/decks",
            data=json.dumps({"title": "Тест"}), headers=headers)
        deck_id = json.loads(res.data)["id"]
        card_ids = []
        for i in range(n):
            res = self.client.post(f"/api/decks/{deck_id}/cards",
                data=json.dumps({"front": f"Q{i}", "back": f"A{i}"}),
                headers=headers)
            card_ids.append(json.loads(res.data)["id"])
        return deck_id, card_ids

    def test_get_cards_for_review(self):
        """Получение карточек для повторения (новые карточки)."""
        headers = self.auth_headers()
        deck_id, _ = self._setup_deck_with_cards(headers)
        res = self.client.get(f"/api/review/today?deck_id={deck_id}",
            headers=headers)
        data = json.loads(res.data)
        self.assertEqual(len(data), 3)

    def test_submit_review(self):
        """Отправка результата повторения."""
        headers = self.auth_headers()
        _, card_ids = self._setup_deck_with_cards(headers, 1)
        res = self.client.post(f"/api/review/{card_ids[0]}",
            data=json.dumps({"quality": 4}), headers=headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("sm2_result", data)
        self.assertEqual(data["sm2_result"]["repetitions"], 1)
        self.assertEqual(data["sm2_result"]["interval"], 1)

    def test_submit_review_invalid_quality(self):
        """Некорректная оценка — ошибка."""
        headers = self.auth_headers()
        _, card_ids = self._setup_deck_with_cards(headers, 1)
        res = self.client.post(f"/api/review/{card_ids[0]}",
            data=json.dumps({"quality": 7}), headers=headers)
        self.assertEqual(res.status_code, 400)

    def test_review_updates_parameters(self):
        """Повторные повторения обновляют параметры."""
        headers = self.auth_headers()
        _, card_ids = self._setup_deck_with_cards(headers, 1)
        card_id = card_ids[0]

        # Первое повторение
        res1 = self.client.post(f"/api/review/{card_id}",
            data=json.dumps({"quality": 5}), headers=headers)
        r1 = json.loads(res1.data)["sm2_result"]

        # Второе повторение
        res2 = self.client.post(f"/api/review/{card_id}",
            data=json.dumps({"quality": 5}), headers=headers)
        r2 = json.loads(res2.data)["sm2_result"]

        self.assertEqual(r2["repetitions"], 2)
        self.assertGreater(r2["interval"], r1["interval"])


class TestStats(BaseTestCase):
    """Тесты статистики."""

    def test_empty_stats(self):
        """Статистика без данных."""
        headers = self.auth_headers()
        res = self.client.get("/api/stats/overview", headers=headers)
        data = json.loads(res.data)
        self.assertEqual(data["total_cards"], 0)
        self.assertEqual(data["reviewed_cards"], 0)

    def test_stats_after_review(self):
        """Статистика после повторения."""
        headers = self.auth_headers()
        # Создаём колоду с карточками
        res = self.client.post("/api/decks",
            data=json.dumps({"title": "Тест"}), headers=headers)
        deck_id = json.loads(res.data)["id"]
        res = self.client.post(f"/api/decks/{deck_id}/cards",
            data=json.dumps({"front": "Q", "back": "A"}), headers=headers)
        card_id = json.loads(res.data)["id"]

        # Повторяем
        self.client.post(f"/api/review/{card_id}",
            data=json.dumps({"quality": 4}), headers=headers)

        # Проверяем статистику
        res = self.client.get("/api/stats/overview", headers=headers)
        data = json.loads(res.data)
        self.assertEqual(data["total_cards"], 1)
        self.assertEqual(data["reviewed_cards"], 1)
        self.assertGreater(len(data["daily_history"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
