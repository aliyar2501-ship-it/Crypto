import uuid

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from market.services import CoinGeckoService

from .forms import AssetForm, RegisterForm
from .models import Asset, UserProfile
from .services import build_portfolio, enrich_asset


def register_view(request):
    if request.user.is_authenticated:
        return redirect('portfolio:list')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            login(request, form.save())
            return redirect('portfolio:list')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def portfolio_list(request):
    data = build_portfolio(request.user)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    page_obj = Paginator(data['assets'], 5).get_page(request.GET.get('page'))
    return render(request, 'portfolio/portfolio_list.html', {**data, 'page_obj': page_obj, 'profile': profile})


@login_required
def asset_detail(request, pk):
    asset = get_object_or_404(Asset, pk=pk, user=request.user)
    prices = CoinGeckoService.get_live_prices([asset.coin_id]) or {}
    enrich_asset(asset, prices.get(asset.coin_id, {}).get('usd'))
    return render(request, 'portfolio/asset_detail.html', {'asset': asset})


@login_required
def asset_create(request):
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.user = request.user
            asset.save()
            messages.success(request, f"Актив {asset.symbol} успешно добавлен!")
            return redirect('portfolio:list')
    else:
        form = AssetForm(initial={'coin_id': request.GET.get('coin_id', '')})
    return render(request, 'portfolio/asset_form.html', {'form': form, 'title': 'Добавить актив'})


@login_required
def asset_update(request, pk):
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
    asset = get_object_or_404(Asset, pk=pk, user=request.user)
    if request.method == 'POST':
        asset.delete()
        messages.success(request, "Актив удалён из портфеля.")
        return redirect('portfolio:list')
    return render(request, 'portfolio/asset_confirm_delete.html', {'asset': asset})


@login_required
@require_POST
def regenerate_key(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.secret_key = uuid.uuid4()
    profile.save(update_fields=['secret_key'])
    messages.success(request, "Новый ключ привязки создан. Старый больше не работает.")
    return redirect('portfolio:list')


@login_required
@require_POST
def unlink_bot(request):
    UserProfile.objects.filter(user=request.user).update(telegram_id=None)
    messages.success(request, "Telegram-бот отключён.")
    return redirect('portfolio:list')