from django.contrib import admin
from .models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('front', 'deck', 'created_at')
    list_filter = ('deck',)
    search_fields = ('front', 'back')
