from rest_framework import serializers
from .models import Deck, DeckRating, Suggestion


class DeckSerializer(serializers.ModelSerializer):
    """Сериализатор колоды."""

    owner = serializers.ReadOnlyField(source='owner.username')
    card_count = serializers.IntegerField(source='cards_count', read_only=True)
    due_count = serializers.SerializerMethodField()
    avg_rating = serializers.ReadOnlyField()
    ratings_count = serializers.ReadOnlyField()
    is_owner = serializers.SerializerMethodField()
    my_rating = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = (
            'id', 'owner', 'title', 'description',
            'is_public', 'card_count', 'due_count',
            'avg_rating', 'ratings_count', 'is_owner', 'my_rating',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at')

    def get_due_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.cards_due_count(request.user)
        return 0

    def get_is_owner(self, obj):
        request = self.context.get('request')
        return bool(request and obj.owner_id == request.user.id)

    def get_my_rating(self, obj):
        """Оценка, которую текущий пользователь поставил этой колоде (или None)."""
        request = self.context.get('request')
        if not (request and request.user.is_authenticated):
            return None
        rating = obj.ratings.filter(user=request.user).first()
        return rating.score if rating else None


class DeckCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления колоды."""

    class Meta:
        model = Deck
        fields = ('title', 'description', 'is_public')


class DeckRatingSerializer(serializers.ModelSerializer):
    """Сериализатор оценки/отзыва о колоде."""

    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = DeckRating
        fields = ('id', 'user', 'score', 'comment', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def validate_score(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Оценка должна быть от 1 до 5.')
        return value


class SuggestionSerializer(serializers.ModelSerializer):
    """Сериализатор предложения (для чтения)."""

    author = serializers.ReadOnlyField(source='author.username')
    suggestion_type_display = serializers.CharField(
        source='get_suggestion_type_display', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # Текущее содержимое целевой карточки (для наглядного сравнения при edit/delete)
    card_front = serializers.CharField(source='card.front', read_only=True, default=None)
    card_back = serializers.CharField(source='card.back', read_only=True, default=None)

    class Meta:
        model = Suggestion
        fields = (
            'id', 'deck', 'card', 'card_front', 'card_back', 'author',
            'suggestion_type', 'suggestion_type_display',
            'front', 'back', 'comment',
            'status', 'status_display', 'created_at', 'resolved_at',
        )
        read_only_fields = fields


class SuggestionCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания предложения."""

    class Meta:
        model = Suggestion
        fields = ('card', 'suggestion_type', 'front', 'back', 'comment')

    def validate(self, attrs):
        stype = attrs.get('suggestion_type')
        card = attrs.get('card')
        front = (attrs.get('front') or '').strip()
        back = (attrs.get('back') or '').strip()

        if stype in (Suggestion.TYPE_EDIT, Suggestion.TYPE_DELETE) and not card:
            raise serializers.ValidationError(
                'Для изменения или удаления нужно указать карточку.'
            )
        if stype in (Suggestion.TYPE_ADD, Suggestion.TYPE_EDIT) and (not front or not back):
            raise serializers.ValidationError(
                'Нужно заполнить обе стороны предлагаемой карточки.'
            )
        # Карточка должна принадлежать той же колоде
        deck = self.context.get('deck')
        if card and deck and card.deck_id != deck.id:
            raise serializers.ValidationError('Карточка не относится к этой колоде.')
        return attrs
