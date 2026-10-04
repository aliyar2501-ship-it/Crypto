import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

MIN_VALUE = Decimal('0.00000001')


class UserProfile(models.Model):
    """Профиль пользователя для связи с Telegram-ботом."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telegram_id = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name='Telegram ID')
    secret_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"Профиль: {self.user.username}"


class Asset(models.Model):
    """Купленная криптовалюта."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assets', verbose_name='Пользователь')
    coin_id = models.CharField(max_length=50, verbose_name='ID монеты в CoinGecko')  # 'bitcoin'
    symbol = models.CharField(max_length=10, verbose_name='Тикер')                    # 'BTC'
    name = models.CharField(max_length=50, verbose_name='Название')                   # 'Bitcoin'
    amount = models.DecimalField(
        max_digits=20, decimal_places=8, validators=[MinValueValidator(MIN_VALUE)],
        verbose_name='Количество монет',
    )
    buy_price = models.DecimalField(
        max_digits=20, decimal_places=8, validators=[MinValueValidator(MIN_VALUE)],
        verbose_name='Цена покупки ($)',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.symbol} - {self.user.username} ({self.amount})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)