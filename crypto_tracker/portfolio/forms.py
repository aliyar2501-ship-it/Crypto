import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from market.services import CoinGeckoError, CoinGeckoService

from .models import Asset

COIN_ID_RE = re.compile(r'^[a-z0-9._-]+$')


class AssetForm(forms.ModelForm):
    """Пользователь вводит только ID монеты; тикер и название берутся из CoinGecko."""

    class Meta:
        model = Asset
        fields = ['coin_id', 'amount', 'buy_price']
        help_texts = {
            'coin_id': 'ID с CoinGecko: bitcoin, ethereum, dogecoin… Кнопка «+» на странице «Рынок» подставит его сама.',
        }
        widgets = {
            'coin_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'например: bitcoin'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': '0.005'}),
            'buy_price': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any',
                                                  'placeholder': 'Цена за 1 монету в USD'}),
        }

    def clean_coin_id(self):
        coin_id = self.cleaned_data['coin_id'].strip().lower()
        if not COIN_ID_RE.fullmatch(coin_id):
            raise ValidationError('Допустимы латинские буквы, цифры и символы - _ .')
        return coin_id

    def clean(self):
        cleaned = super().clean()
        coin_id = cleaned.get('coin_id')
        if not coin_id:
            return cleaned

        # Монета не менялась — обращаться к API незачем
        if self.instance.pk and self.instance.coin_id == coin_id:
            return cleaned

        try:
            info = CoinGeckoService.get_coin(coin_id)
        except CoinGeckoError:
            self.add_error('coin_id', 'Не удалось проверить монету: CoinGecko сейчас недоступен. '
                                      'Попробуйте через минуту.')
            return cleaned

        if info is None:
            self.add_error('coin_id', f'Монета «{coin_id}» не найдена в CoinGecko. '
                                      'Проверьте ID на странице «Рынок».')
            return cleaned

        self.instance.symbol = info['symbol'][:10]
        self.instance.name = info['name'][:50]
        return cleaned


class RegisterForm(UserCreationForm):
    """Регистрация со стилями Bootstrap (вместо JS-хака в шаблоне)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')