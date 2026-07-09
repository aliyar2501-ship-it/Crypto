from rest_framework import serializers
from portfolio.models import Asset, UserProfile


class AssetSerializer(serializers.ModelSerializer):
    """Превращает данные о монете в JSON."""

    class Meta:
        model = Asset
        fields = ['coin_id', 'symbol', 'name', 'amount', 'buy_price']


class UserProfileSerializer(serializers.ModelSerializer):
    """Превращает профиль пользователя в JSON."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['username', 'telegram_id', 'secret_key']