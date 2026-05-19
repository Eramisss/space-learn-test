from django.urls import path
from .views import today_cards, submit_review

urlpatterns = [
    path('today/', today_cards, name='review-today'),
    path('<int:card_id>/', submit_review, name='review-submit'),
]
