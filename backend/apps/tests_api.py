"""
Тесты API-эндпоинтов.

Тестовый план:
1. Регистрация пользователя
2. Аутентификация (получение JWT)
3. CRUD колод
4. CRUD карточек
5. Получение карточек на повторение
6. Отправка результата повторения
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from apps.decks.models import Deck
from apps.cards.models import Card
from apps.accounts.models import Profile


class AuthAPITest(TestCase):
    """Тесты аутентификации."""

    def setUp(self):
        self.client = APIClient()

    def test_register(self):
        """Регистрация нового пользователя."""
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_duplicate_email(self):
        """Регистрация с существующим email отклоняется."""
        User.objects.create_user('existing', 'dup@test.com', 'pass123456')
        Profile.objects.create(user=User.objects.get(username='existing'))
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser2',
            'email': 'dup@test.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login(self):
        """Получение JWT-токена."""
        User.objects.create_user('loginuser', 'login@test.com', 'TestPass123!')
        response = self.client.post('/api/auth/login/', {
            'username': 'loginuser',
            'password': 'TestPass123!',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class DeckAPITest(TestCase):
    """Тесты API колод."""

    def setUp(self):
        self.user = User.objects.create_user('deckuser', 'deck@test.com', 'TestPass123!')
        Profile.objects.create(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_deck(self):
        """Создание колоды."""
        response = self.client.post('/api/decks/', {
            'title': 'Python Basics',
            'description': 'Основы Python',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Deck.objects.count(), 1)

    def test_list_decks(self):
        """Получение списка колод."""
        Deck.objects.create(owner=self.user, title='Deck 1')
        Deck.objects.create(owner=self.user, title='Deck 2')
        response = self.client.get('/api/decks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_delete_deck(self):
        """Удаление колоды."""
        deck = Deck.objects.create(owner=self.user, title='To Delete')
        response = self.client.delete(f'/api/decks/{deck.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Deck.objects.count(), 0)


class CardAPITest(TestCase):
    """Тесты API карточек."""

    def setUp(self):
        self.user = User.objects.create_user('carduser', 'card@test.com', 'TestPass123!')
        Profile.objects.create(user=self.user)
        self.deck = Deck.objects.create(owner=self.user, title='Test Deck')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_card(self):
        """Создание карточки."""
        response = self.client.post(f'/api/cards/deck/{self.deck.id}/', {
            'front': 'What is Django?',
            'back': 'Python web framework',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Card.objects.count(), 1)

    def test_list_cards_in_deck(self):
        """Список карточек в колоде."""
        Card.objects.create(deck=self.deck, front='Q1', back='A1')
        Card.objects.create(deck=self.deck, front='Q2', back='A2')
        response = self.client.get(f'/api/cards/deck/{self.deck.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_csv_import(self):
        """Импорт карточек из CSV."""
        csv_data = 'Python;Язык программирования\nDjango;Веб-фреймворк\nReact;JS-библиотека'
        response = self.client.post(
            f'/api/cards/deck/{self.deck.id}/import/',
            {'csv_data': csv_data},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Card.objects.filter(deck=self.deck).count(), 3)


class ReviewAPITest(TestCase):
    """Тесты API повторений."""

    def setUp(self):
        self.user = User.objects.create_user('revuser', 'rev@test.com', 'TestPass123!')
        Profile.objects.create(user=self.user)
        self.deck = Deck.objects.create(owner=self.user, title='Review Deck')
        self.card = Card.objects.create(deck=self.deck, front='Q', back='A')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_today_cards_includes_new(self):
        """Новые карточки включаются в список на сегодня."""
        response = self.client.get('/api/review/today/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['new_count'], 1)

    def test_submit_review(self):
        """Отправка результата повторения."""
        response = self.client.post(f'/api/review/{self.card.id}/', {
            'quality': 4,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('new_ef', response.data)
        self.assertIn('next_review', response.data)

    def test_submit_invalid_quality(self):
        """Некорректная оценка (q > 5) отклоняется."""
        response = self.client.post(f'/api/review/{self.card.id}/', {
            'quality': 6,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
