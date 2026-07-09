from django import forms
from .models import Asset

class AssetForm(forms.ModelForm):
    """Форма для добавления и редактирования криптоактива."""
    class Meta:
        model = Asset
        fields = ['coin_id', 'symbol', 'name', 'amount', 'buy_price']
        widgets = {
            'coin_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'например: bitcoin'}),
            'symbol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'например: BTC'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'например: Bitcoin'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': '0.005'}),
            'buy_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Цена за 1 монету в USD'}),
        }