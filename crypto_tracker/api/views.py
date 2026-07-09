from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from portfolio.models import UserProfile, Asset
from market.services import CoinGeckoService


@api_view(['POST'])
def link_telegram(request):
    """Эндпоинт для привязки Telegram-бота к аккаунту на сайте."""
    secret_key = request.data.get('secret_key')
    telegram_id = request.data.get('telegram_id')

    if not secret_key or not telegram_id:
        return Response({'error': 'Необходимы secret_key и telegram_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Ищем пользователя по секретному ключу
        profile = UserProfile.objects.get(secret_key=secret_key)
        profile.telegram_id = str(telegram_id)
        profile.save()
        return Response({
            'message': 'Аккаунт успешно привязан!',
            'username': profile.user.username
        })
    except UserProfile.DoesNotExist:
        return Response({'error': 'Неверный секретный ключ или аккаунт не существует'},
                        status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_bot_portfolio(request):
    """Эндпоинт для получения портфеля бота (возвращает PnL и активы)."""
    telegram_id = request.GET.get('telegram_id')

    if not telegram_id:
        return Response({'error': 'Не указан telegram_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Находим пользователя сайта по его Telegram ID
        profile = UserProfile.objects.get(telegram_id=telegram_id)
    except UserProfile.DoesNotExist:
        return Response({'error': 'Пользователь не привязан к боту'}, status=status.HTTP_404_NOT_FOUND)

    # Получаем его активы
    assets = Asset.objects.filter(user=profile.user)
    if not assets.exists():
        return Response({
            'username': profile.user.username,
            'total_invested': 0,
            'total_current_value': 0,
            'assets': []
        })

    # Подтягиваем актуальные цены из CoinGecko
    coin_ids = list(assets.values_list('coin_id', flat=True).distinct())
    live_prices = CoinGeckoService.get_live_prices(coin_ids)

    assets_data = []
    total_invested = 0
    total_current_value = 0

    # Считаем PnL для API (аналогично тому, как делали для сайта)
    for asset in assets:
        current_price = float(live_prices.get(asset.coin_id, {}).get('usd', asset.buy_price))
        buy_price = float(asset.buy_price)
        amount = float(asset.amount)

        invested = buy_price * amount
        current_val = current_price * amount
        pnl = current_val - invested

        total_invested += invested
        total_current_value += current_val

        assets_data.append({
            'symbol': asset.symbol.upper(),
            'name': asset.name,
            'amount': amount,
            'buy_price': buy_price,
            'current_price': current_price,
            'current_value': round(current_val, 2),
            'pnl_usd': round(pnl, 2)
        })

    return Response({
        'username': profile.user.username,
        'total_invested': round(total_invested, 2),
        'total_current_value': round(total_current_value, 2),
        'total_pnl_usd': round(total_current_value - total_invested, 2),
        'assets': assets_data
    })