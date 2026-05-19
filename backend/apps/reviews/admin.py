from django.contrib import admin
from .models import ReviewLog


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'card', 'quality', 'easiness_factor', 'interval_days', 'next_review', 'reviewed_at')
    list_filter = ('quality', 'reviewed_at')
    search_fields = ('user__username', 'card__front')
