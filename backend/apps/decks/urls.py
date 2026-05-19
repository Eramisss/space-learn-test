from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.cards.views import CardViewSet, import_csv
from .views import DeckViewSet

router = DefaultRouter()
router.register('', DeckViewSet, basename='deck')

# Вложенные карточки колоды — фронт ожидает /api/decks/{id}/cards/ и /api/decks/{id}/import/
deck_cards = CardViewSet.as_view({'get': 'list', 'post': 'create'})

urlpatterns = [
    path('<int:deck_id>/cards/', deck_cards, name='deck-cards'),
    path('<int:deck_id>/import/', import_csv, name='deck-import'),
    path('', include(router.urls)),
]
