from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from portfolio.models import Asset

SECRET = 's3cret'
AUTH = {'X-Bot-Secret': SECRET}


@override_settings(BOT_API_SECRET=SECRET)
class BotApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345!')
        self.profile = self.user.profile

    def post(self, name, payload, headers=AUTH):
        return self.client.post(reverse(f'api:{name}'), payload,
                                content_type='application/json', headers=headers)

    def test_requires_secret(self):
        response = self.client.get(reverse('api:bot_portfolio'), {'telegram_id': '1'})
        self.assertEqual(response.status_code, 403)
        response = self.post('link_bot', {'secret_key': 'x', 'telegram_id': '1'}, headers={})
        self.assertEqual(response.status_code, 403)

    def test_link_invalid_uuid(self):
        response = self.post('link_bot', {'secret_key': 'abc', 'telegram_id': '555'})
        self.assertEqual(response.status_code, 400)

    def test_link_unknown_key(self):
        response = self.post('link_bot', {'secret_key': '00000000-0000-0000-0000-000000000000',
                                          'telegram_id': '555'})
        self.assertEqual(response.status_code, 404)

    def test_link_success_rotates_key(self):
        old_key = self.profile.secret_key
        response = self.post('link_bot', {'secret_key': str(old_key), 'telegram_id': '555'})
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.telegram_id, '555')
        self.assertNotEqual(self.profile.secret_key, old_key)

    def test_link_moves_telegram_id_from_other_account(self):
        bob = User.objects.create_user('bob', password='pass12345!')
        bob.profile.telegram_id = '555'
        bob.profile.save()
        response = self.post('link_bot', {'secret_key': str(self.profile.secret_key), 'telegram_id': '555'})
        self.assertEqual(response.status_code, 200)
        bob.profile.refresh_from_db()
        self.assertIsNone(bob.profile.telegram_id)

    def test_portfolio_not_linked(self):
        response = self.client.get(reverse('api:bot_portfolio'), {'telegram_id': '999'}, headers=AUTH)
        self.assertEqual(response.status_code, 404)

    def test_empty_portfolio_has_all_fields(self):
        self.profile.telegram_id = '555'
        self.profile.save()
        response = self.client.get(reverse('api:bot_portfolio'), {'telegram_id': '555'}, headers=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_pnl_usd'], 0)
        self.assertEqual(response.json()['assets'], [])

    @patch('portfolio.services.CoinGeckoService.get_live_prices', return_value={'bitcoin': {'usd': 150}})
    def test_portfolio_data(self, _):
        self.profile.telegram_id = '555'
        self.profile.save()
        Asset.objects.create(user=self.user, coin_id='bitcoin', symbol='BTC', name='Bitcoin',
                             amount=Decimal('2'), buy_price=Decimal('100'))
        response = self.client.get(reverse('api:bot_portfolio'), {'telegram_id': '555'}, headers=AUTH)
        data = response.json()
        self.assertEqual(data['total_pnl_usd'], 100)
        self.assertTrue(data['prices_ok'])