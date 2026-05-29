from django.contrib import admin
from .models import Deck, DeckRating, Suggestion


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'is_public', 'cards_count', 'avg_rating', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('title', 'owner__username')


@admin.register(DeckRating)
class DeckRatingAdmin(admin.ModelAdmin):
    list_display = ('deck', 'user', 'score', 'updated_at')
    list_filter = ('score',)
    search_fields = ('deck__title', 'user__username')


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ('deck', 'author', 'suggestion_type', 'status', 'created_at')
    list_filter = ('suggestion_type', 'status')
    search_fields = ('deck__title', 'author__username')
