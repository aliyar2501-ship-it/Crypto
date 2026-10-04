from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import AssetForm
from .models import Asset
from .services import build_portfolio


class BuildPortfolioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345!')
        Asset.objects.create(user=self.user, coin_id='bitcoin', symbol='BTC', name='Bitcoin',
                             amount=Decimal('2'), buy_price=Decimal('100'))

    @patch('portfolio.services.CoinGeckoService.get_live_prices', return_value={'bitcoin': {'usd': 150}})
    def test_pnl(self, _):
        data = build_portfolio(self.user)
        self.assertEqual(data['total_invested'], Decimal('200'))
        self.assertEqual(data['total_current_value'], Decimal('300'))
        self.assertEqual(data['total_pnl_usd'], Decimal('100'))
        self.assertEqual(data['total_pnl_percent'], Decimal('50'))
        self.assertTrue(data['prices_ok'])

    @patch('portfolio.services.CoinGeckoService.get_live_prices', return_value=None)
    def test_prices_unavailable(self, _):
        data = build_portfolio(self.user)
        self.assertFalse(data['prices_ok'])
        self.assertEqual(data['missing_symbols'], ['BTC'])
        self.assertEqual(data['total_pnl_usd'], Decimal('0'))


class AssetAccessTests(TestCase):
    def test_other_users_asset_is_404(self):
        alice = User.objects.create_user('alice', password='pass12345!')
        User.objects.create_user('bob', password='pass12345!')
        asset = Asset.objects.create(user=alice, coin_id='bitcoin', symbol='BTC', name='Bitcoin',
                                     amount=Decimal('1'), buy_price=Decimal('10'))
        self.client.login(username='bob', password='pass12345!')
        for name in ('detail', 'update', 'delete'):
            response = self.client.get(reverse(f'portfolio:{name}', args=[asset.pk]))
            self.assertEqual(response.status_code, 404, name)


class AssetFormTests(TestCase):
    @patch('portfolio.forms.CoinGeckoService.get_coin', return_value=None)
    def test_unknown_coin(self, _):
        form = AssetForm({'coin_id': 'bitcon', 'amount': '1', 'buy_price': '10'})
        self.assertFalse(form.is_valid())
        self.assertIn('coin_id', form.errors)

    @patch('portfolio.forms.CoinGeckoService.get_coin',
           return_value={'id': 'bitcoin', 'symbol': 'BTC', 'name': 'Bitcoin'})
    def test_symbol_and_name_are_filled(self, _):
        form = AssetForm({'coin_id': ' Bitcoin ', 'amount': '1', 'buy_price': '10'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.coin_id, 'bitcoin')
        self.assertEqual(form.instance.symbol, 'BTC')

    @patch('portfolio.forms.CoinGeckoService.get_coin',
           return_value={'id': 'bitcoin', 'symbol': 'BTC', 'name': 'Bitcoin'})
    def test_negative_amount_rejected(self, _):
        form = AssetForm({'coin_id': 'bitcoin', 'amount': '-1', 'buy_price': '10'})
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)