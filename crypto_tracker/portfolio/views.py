from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Asset
from .forms import AssetForm
from market.services import CoinGeckoService


def register_view(request):
    """View-функция для регистрации нового пользователя."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def portfolio_list(request):
    """Главная страница портфеля с расчетом PnL и пагинацией."""

    user_assets = Asset.objects.filter(user=request.user).order_by('-created_at')

    # Собираем уникальные coin_id, чтобы сделать один запрос к API вместо десятка
    coin_ids = list(user_assets.values_list('coin_id', flat=True).distinct())
    live_prices = CoinGeckoService.get_live_prices(coin_ids)


    total_invested = 0
    total_current_value = 0

    # Просчитываем динамические данные для каждого актива
    for asset in user_assets:
        current_price = live_prices.get(asset.coin_id, {}).get('usd', float(asset.buy_price))
        current_price = float(current_price)
        buy_price = float(asset.buy_price)
        amount = float(asset.amount)


        asset.current_price = current_price
        asset.total_buy_cost = buy_price * amount
        asset.current_value = current_price * amount
        asset.pnl_usd = asset.current_value - asset.total_buy_cost

        if buy_price > 0:
            asset.pnl_percent = ((current_price - buy_price) / buy_price) * 100
        else:
            asset.pnl_percent = 0


        total_invested += asset.total_buy_cost
        total_current_value += asset.current_value


    total_pnl_usd = total_current_value - total_invested
    total_pnl_percent = ((total_current_value - total_invested) / total_invested * 100) if total_invested > 0 else 0


    paginator = Paginator(user_assets, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'portfolio/portfolio_list.html', {
        'page_obj': page_obj,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_pnl_usd': total_pnl_usd,
        'total_pnl_percent': total_pnl_percent,
    })


@login_required
def asset_detail(request, pk):
    """Детальная страница актива."""
    asset = get_object_or_404(Asset, pk=pk, user=request.user)
    return render(request, 'portfolio/asset_detail.html', {'asset': asset})


@login_required
def asset_create(request):
    """Добавление нового актива в портфель."""
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.user = request.user  # Привязываем к текущему юзеру
            asset.save()
            messages.success(request, f"Актив {asset.symbol} успешно добавлен!")
            return redirect('portfolio:list')
    else:
        form = AssetForm()
    return render(request, 'portfolio/asset_form.html', {'form': form, 'title': 'Добавить актив'})


@login_required
def asset_update(request, pk):
    """Редактирование актива."""
    asset = get_object_or_404(Asset, pk=pk, user=request.user)
    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            messages.success(request, f"Запись по {asset.symbol} обновлена.")
            return redirect('portfolio:list')
    else:
        form = AssetForm(instance=asset)
    return render(request, 'portfolio/asset_form.html', {'form': form, 'title': 'Редактировать актив'})


@login_required
def asset_delete(request, pk):
    """Удаление актива из портфеля."""
    asset = get_object_or_404(Asset, pk=pk, user=request.user)
    if request.method == 'POST':
        asset.delete()
        messages.success(request, "Актив удален из портфеля.")
        return redirect('portfolio:list')
    return render(request, 'portfolio/asset_confirm_delete.html', {'asset': asset})