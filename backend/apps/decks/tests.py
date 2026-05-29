"""
Тесты социальных функций колод: публикация, каталог, копирование,
оценки (рейтинги) и предложения улучшений.
"""

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from apps.cards.models import Card
from .models import Deck, DeckRating, Suggestion


class SocialDecksTest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass12345')
        self.other = User.objects.create_user('other', password='pass12345')
        self.deck = Deck.objects.create(
            owner=self.owner, title='Публичная колода',
            description='desc', is_public=True,
        )
        self.card = Card.objects.create(deck=self.deck, front='Q1', back='A1')

    def auth(self, user):
        self.client.force_authenticate(user=user)

    # ---------- Публикация и каталог ----------
    def test_publish_toggle(self):
        self.auth(self.owner)
        priv = Deck.objects.create(owner=self.owner, title='Приватная', is_public=False)
        resp = self.client.patch(f'/api/decks/{priv.id}/', {'is_public': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        priv.refresh_from_db()
        self.assertTrue(priv.is_public)

    def test_catalog_lists_others_public(self):
        self.auth(self.other)
        resp = self.client.get('/api/decks/public/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [d['id'] for d in resp.data]
        self.assertIn(self.deck.id, ids)

    def test_catalog_excludes_own(self):
        self.auth(self.owner)
        resp = self.client.get('/api/decks/public/')
        self.assertNotIn(self.deck.id, [d['id'] for d in resp.data])

    # ---------- Копирование чужой публичной колоды ----------
    def test_clone_public_deck(self):
        self.auth(self.other)
        resp = self.client.post(f'/api/decks/{self.deck.id}/clone/')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        clone = Deck.objects.get(id=resp.data['id'])
        self.assertEqual(clone.owner, self.other)
        self.assertEqual(clone.cards.count(), 1)

    def test_cannot_clone_private_foreign_deck(self):
        priv = Deck.objects.create(owner=self.owner, title='Секрет', is_public=False)
        self.auth(self.other)
        resp = self.client.post(f'/api/decks/{priv.id}/clone/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ---------- Оценки ----------
    def test_rate_and_average(self):
        self.auth(self.other)
        resp = self.client.post(f'/api/decks/{self.deck.id}/ratings/',
                                {'score': 5, 'comment': 'отлично'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        third = User.objects.create_user('third', password='pass12345')
        self.auth(third)
        self.client.post(f'/api/decks/{self.deck.id}/ratings/', {'score': 3}, format='json')
        self.deck.refresh_from_db()
        self.assertEqual(self.deck.ratings_count, 2)
        self.assertEqual(self.deck.avg_rating, 4.0)

    def test_rating_is_updated_not_duplicated(self):
        self.auth(self.other)
        self.client.post(f'/api/decks/{self.deck.id}/ratings/', {'score': 2}, format='json')
        self.client.post(f'/api/decks/{self.deck.id}/ratings/', {'score': 4}, format='json')
        self.assertEqual(DeckRating.objects.filter(deck=self.deck, user=self.other).count(), 1)
        self.assertEqual(self.deck.avg_rating, 4.0)

    def test_cannot_rate_own_deck(self):
        self.auth(self.owner)
        resp = self.client.post(f'/api/decks/{self.deck.id}/ratings/', {'score': 5}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- Предложения улучшений ----------
    def test_suggest_add_and_accept(self):
        self.auth(self.other)
        resp = self.client.post(f'/api/decks/{self.deck.id}/suggestions/', {
            'suggestion_type': 'add', 'front': 'Q2', 'back': 'A2',
            'comment': 'добавьте это',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        sug_id = resp.data['id']

        self.auth(self.owner)
        resp = self.client.post(f'/api/decks/suggestions/{sug_id}/resolve/',
                                {'action': 'accept'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'accepted')
        self.assertTrue(self.deck.cards.filter(front='Q2', back='A2').exists())

    def test_suggest_edit_and_accept_changes_card(self):
        sug = Suggestion.objects.create(
            deck=self.deck, card=self.card, author=self.other,
            suggestion_type='edit', front='Q1-new', back='A1-new',
        )
        self.auth(self.owner)
        self.client.post(f'/api/decks/suggestions/{sug.id}/resolve/',
                         {'action': 'accept'}, format='json')
        self.card.refresh_from_db()
        self.assertEqual(self.card.front, 'Q1-new')
        self.assertEqual(self.card.back, 'A1-new')

    def test_suggest_delete_and_accept_removes_card(self):
        sug = Suggestion.objects.create(
            deck=self.deck, card=self.card, author=self.other,
            suggestion_type='delete',
        )
        self.auth(self.owner)
        self.client.post(f'/api/decks/suggestions/{sug.id}/resolve/',
                         {'action': 'accept'}, format='json')
        self.assertFalse(Card.objects.filter(id=self.card.id).exists())
        # Предложение сохраняется как история (card → NULL)
        sug.refresh_from_db()
        self.assertEqual(sug.status, 'accepted')
        self.assertIsNone(sug.card_id)

    def test_reject_does_not_apply(self):
        sug = Suggestion.objects.create(
            deck=self.deck, card=self.card, author=self.other,
            suggestion_type='edit', front='X', back='Y',
        )
        self.auth(self.owner)
        self.client.post(f'/api/decks/suggestions/{sug.id}/resolve/',
                         {'action': 'reject'}, format='json')
        self.card.refresh_from_db()
        self.assertEqual(self.card.front, 'Q1')  # не изменилось
        sug.refresh_from_db()
        self.assertEqual(sug.status, 'rejected')

    def test_non_owner_cannot_resolve(self):
        sug = Suggestion.objects.create(
            deck=self.deck, card=self.card, author=self.other,
            suggestion_type='delete',
        )
        self.auth(self.other)
        resp = self.client.post(f'/api/decks/suggestions/{sug.id}/resolve/',
                                {'action': 'accept'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_sees_all_suggestions_others_see_only_own(self):
        Suggestion.objects.create(deck=self.deck, card=self.card, author=self.other,
                                  suggestion_type='delete')
        third = User.objects.create_user('third', password='pass12345')
        Suggestion.objects.create(deck=self.deck, author=third,
                                  suggestion_type='add', front='Z', back='W')
        self.auth(self.owner)
        resp = self.client.get(f'/api/decks/{self.deck.id}/suggestions/')
        self.assertEqual(len(resp.data), 2)
        self.auth(self.other)
        resp = self.client.get(f'/api/decks/{self.deck.id}/suggestions/')
        self.assertEqual(len(resp.data), 1)
