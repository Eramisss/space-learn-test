from django.urls import path
from .views import overview, history, heatmap

urlpatterns = [
    path('overview/', overview, name='stats-overview'),
    path('history/', history, name='stats-history'),
    path('heatmap/', heatmap, name='stats-heatmap'),
]
