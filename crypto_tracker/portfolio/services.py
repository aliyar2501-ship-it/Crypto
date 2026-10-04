from decimal import Decimal

from market.services import CoinGeckoService

from .models import Asset

ZERO = Decimal('0')
HUNDRED = Decimal('100')


def enrich_asset(asset, raw_price):
    """Добавляет к активу расчётные поля. raw_price=None, если цену получить не удалось."""
    asset.price_known = raw_price is not None
    asset.current_price = Decimal(str(raw_price)) if asset.price_known else asset.buy_price
    asset.total_buy_cost = asset.buy_price * asset.amount
    asset.current_value = asset.current_price * asset.amount
    asset.pnl_usd = asset.current_value - asset.total_buy_cost
    if asset.total_buy_cost > 0:
        asset.pnl_percent = asset.pnl_usd / asset.total_buy_cost * HUNDRED
    else:
        asset.pnl_percent = ZERO
    return asset


def build_portfolio(user):
    assets = list(Asset.objects.filter(user=user).order_by('-created_at'))
    prices = CoinGeckoService.get_live_prices({a.coin_id for a in assets}) or {}

    total_invested = ZERO
    total_value = ZERO
    for asset in assets:
        enrich_asset(asset, prices.get(asset.coin_id, {}).get('usd'))
        total_invested += asset.total_buy_cost
        total_value += asset.current_value

    missing = sorted({a.symbol for a in assets if not a.price_known})
    total_pnl = total_value - total_invested
    total_pnl_percent = total_pnl / total_invested * HUNDRED if total_invested > 0 else ZERO

    return {
        'assets': assets,
        'total_invested': total_invested,
        'total_current_value': total_value,
        'total_pnl_usd': total_pnl,
        'total_pnl_percent': total_pnl_percent,
        'prices_ok': not missing,
        'missing_symbols': missing,
    }