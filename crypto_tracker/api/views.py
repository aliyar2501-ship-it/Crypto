import uuid

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from portfolio.models import UserProfile
from portfolio.services import build_portfolio

# Доступ ко всем view проверяет HasBotSecret (DEFAULT_PERMISSION_CLASSES в settings.py)


@api_view(['POST'])
def link_telegram(request):
    raw_key = request.data.get('secret_key')
    telegram_id = request.data.get('telegram_id')
    if not raw_key or not telegram_id:
        return Response({'error': 'Необходимы secret_key и telegram_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        key = uuid.UUID(str(raw_key).strip())
    except ValueError:
        return Response({'error': 'Неверный формат ключа. Скопируйте его со страницы портфеля.'},
                        status=status.HTTP_400_BAD_REQUEST)

    telegram_id = str(telegram_id).strip()
    try:
        profile = UserProfile.objects.select_related('user').get(secret_key=key)
    except UserProfile.DoesNotExist:
        return Response({'error': 'Неверный секретный ключ'}, status=status.HTTP_404_NOT_FOUND)

    with transaction.atomic():
        # Этот Telegram мог быть привязан к другому аккаунту — освобождаем его (unique)
        UserProfile.objects.filter(telegram_id=telegram_id).exclude(pk=profile.pk).update(telegram_id=None)
        profile.telegram_id = telegram_id
        profile.secret_key = uuid.uuid4()   # ключ одноразовый: старый остался в истории чата
        profile.save(update_fields=['telegram_id', 'secret_key'])

    return Response({'message': 'Аккаунт успешно привязан!', 'username': profile.user.username})


@api_view(['POST'])
def unlink_telegram(request):
    telegram_id = str(request.data.get('telegram_id', '')).strip()
    if not telegram_id:
        return Response({'error': 'Не указан telegram_id'}, status=status.HTTP_400_BAD_REQUEST)
    updated = UserProfile.objects.filter(telegram_id=telegram_id).update(telegram_id=None)
    if not updated:
        return Response({'error': 'Аккаунт не был привязан'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'message': 'Привязка снята'})


@api_view(['GET'])
def get_bot_portfolio(request):
    telegram_id = request.GET.get('telegram_id', '').strip()
    if not telegram_id:
        return Response({'error': 'Не указан telegram_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        profile = UserProfile.objects.select_related('user').get(telegram_id=telegram_id)
    except UserProfile.DoesNotExist:
        return Response({'error': 'Пользователь не привязан к боту'}, status=status.HTTP_404_NOT_FOUND)

    data = build_portfolio(profile.user)   # тот же расчёт, что и на сайте; поля есть и при пустом портфеле
    return Response({
        'username': profile.user.username,
        'total_invested': float(data['total_invested']),
        'total_current_value': float(data['total_current_value']),
        'total_pnl_usd': float(data['total_pnl_usd']),
        'total_pnl_percent': float(data['total_pnl_percent']),
        'prices_ok': data['prices_ok'],
        'missing_symbols': data['missing_symbols'],
        'assets': [
            {
                'symbol': a.symbol.upper(),
                'name': a.name,
                'amount': float(a.amount),
                'buy_price': float(a.buy_price),
                'current_price': float(a.current_price),
                'current_value': float(a.current_value),
                'pnl_usd': float(a.pnl_usd),
                'pnl_percent': float(a.pnl_percent),
                'price_known': a.price_known,
            }
            for a in data['assets']
        ],
    })