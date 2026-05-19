"""
URL Configuration — маршрутизация API.
Все API-эндпоинты доступны по префиксу /api/.
"""

from pathlib import Path

from django.contrib import admin
from django.http import FileResponse
from django.urls import path, include


def spa_view(request):
    """Отдаём frontend/index.html как статический файл (минуя шаблонизатор)."""
    frontend_path = Path(__file__).resolve().parent.parent.parent / 'frontend' / 'index.html'
    return FileResponse(open(frontend_path, 'rb'), content_type='text/html; charset=utf-8')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/decks/', include('apps.decks.urls')),
    path('api/cards/', include('apps.cards.urls')),
    path('api/review/', include('apps.reviews.urls')),
    path('api/stats/', include('apps.stats.urls')),
    # Django сам отдаёт фронтенд (один origin → не нужен CORS, не нужен http.server)
    path('', spa_view, name='spa'),
]
