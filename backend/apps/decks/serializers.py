from rest_framework import serializers
from .models import Deck


class DeckSerializer(serializers.ModelSerializer):
    """Сериализатор колоды."""

    owner = serializers.ReadOnlyField(source='owner.username')
    card_count = serializers.IntegerField(source='cards_count', read_only=True)
    due_count = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = (
            'id', 'owner', 'title', 'description',
            'is_public', 'card_count', 'due_count',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at')

    def get_due_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.cards_due_count(request.user)
        return 0


class DeckCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления колоды."""

    class Meta:
        model = Deck
        fields = ('title', 'description', 'is_public')
