from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'daily_new_cards_limit', 'created_at')
    search_fields = ('user__username', 'user__email')
