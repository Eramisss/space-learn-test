from rest_framework import serializers
from apps.cards.serializers import CardSerializer


class ReviewSubmitSerializer(serializers.Serializer):
    """Сериализатор для отправки результата повторения."""
    quality = serializers.IntegerField(min_value=0, max_value=5)


class ReviewResultSerializer(serializers.Serializer):
    """Сериализатор ответа после повторения."""
    card_id = serializers.IntegerField()
    quality = serializers.IntegerField()
    new_ef = serializers.FloatField()
    new_interval = serializers.IntegerField()
    next_review = serializers.DateField()
    repetitions = serializers.IntegerField()


class CardForReviewSerializer(serializers.Serializer):
    """Карточка, подготовленная для повторения."""
    id = serializers.IntegerField()
    front = serializers.CharField()
    back = serializers.CharField()
    deck_id = serializers.IntegerField()
    deck_title = serializers.CharField()
    is_new = serializers.BooleanField()
    current_ef = serializers.FloatField()
    current_interval = serializers.IntegerField()
