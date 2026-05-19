from django.urls import path
from .views import CardViewSet, import_csv

# Вложенные маршруты: карточки внутри колоды
card_list = CardViewSet.as_view({'get': 'list', 'post': 'create'})
card_detail = CardViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})

urlpatterns = [
    path('deck/<int:deck_id>/', card_list, name='card-list'),
    path('deck/<int:deck_id>/import/', import_csv, name='card-import'),
    path('<int:pk>/', card_detail, name='card-detail'),
]
