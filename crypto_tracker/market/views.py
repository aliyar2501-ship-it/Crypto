from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.shortcuts import render

from .services import CoinGeckoService


def market_view(request):
    search_query = request.GET.get('search', '').strip()[:50]
    needle = search_query.lower()

    coins = CoinGeckoService.get_top_coins(per_page=100)
    api_error = coins is None
    coins = coins or []

    if needle:
        coins = [c for c in coins
                 if needle in (c.get('name') or '').lower() or needle in (c.get('symbol') or '').lower()]

    page_obj = Paginator(coins, 10).get_page(request.GET.get('page'))
    extra_query = '&' + urlencode({'search': search_query}) if search_query else ''

    return render(request, 'market/market.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'extra_query': extra_query,
        'api_error': api_error,
    })