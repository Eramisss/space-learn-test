import csv
import io
from rest_framework import serializers
from .models import Card


class CardSerializer(serializers.ModelSerializer):
    """Сериализатор карточки."""

    class Meta:
        model = Card
        fields = ('id', 'deck', 'front', 'back', 'created_at')
        read_only_fields = ('id', 'created_at')


class CardCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания карточки (без указания колоды — она из URL)."""

    class Meta:
        model = Card
        fields = ('front', 'back')


class CSVImportSerializer(serializers.Serializer):
    """Сериализатор для импорта карточек из CSV."""
    csv_data = serializers.CharField(
        help_text='CSV-данные: каждая строка — front;back'
    )

    def validate_csv_data(self, value):
        """Парсинг и валидация CSV."""
        reader = csv.reader(io.StringIO(value), delimiter=';')
        cards = []
        for i, row in enumerate(reader, 1):
            if len(row) < 2:
                raise serializers.ValidationError(
                    f'Строка {i}: ожидается минимум 2 столбца (front;back).'
                )
            front = row[0].strip()
            back = row[1].strip()
            if not front or not back:
                raise serializers.ValidationError(
                    f'Строка {i}: пустые значения не допускаются.'
                )
            cards.append({'front': front, 'back': back})
        if not cards:
            raise serializers.ValidationError('CSV не содержит данных.')
        return cards
