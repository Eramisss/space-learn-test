from django.contrib import admin
from .models import Deck


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'is_public', 'cards_count', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('title', 'owner__username')
