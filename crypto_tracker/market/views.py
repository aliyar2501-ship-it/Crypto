from django.shortcuts import render
from django.core.paginator import Paginator
from .services import CoinGeckoService


def market_view(request):
    """Отображение страницы 'Рынок' с поиском и пагинацией."""
    search_query = request.GET.get('search', '').strip().lower()


    coins = CoinGeckoService.get_top_coins(per_page=100)


    if search_query:
        coins = [
            coin for coin in coins
            if search_query in coin['name'].lower() or search_query in coin['symbol'].lower()
        ]


    paginator = Paginator(coins, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'market/market.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })