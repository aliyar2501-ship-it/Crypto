from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _to_decimal(value):
    if value is None or value == '':
        return None
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


def _fmt(a):
    """Неотрицательное Decimal -> '1,234.56'; для дешёвых монет до 8 знаков."""
    digits = 2 if (a == 0 or a >= 1) else min(8, max(2, 2 - a.adjusted()))
    return f'{a:,.{digits}f}'


@register.filter
def usd(value):
    """$1,234.56 / -$5.00 / $0.00000123"""
    d = _to_decimal(value)
    if d is None:
        return '—'
    text = _fmt(abs(d))
    sign = '-' if d < 0 and text.strip('0.,') else ''
    return f'{sign}${text}'


@register.filter
def signed_usd(value):
    """+$12.00 / -$5.00"""
    d = _to_decimal(value)
    if d is None:
        return '—'
    text = _fmt(abs(d))
    sign = '-' if d < 0 and text.strip('0.,') else '+'
    return f'{sign}${text}'


@register.filter
def pct(value):
    """+12.34% / -5.00%"""
    d = _to_decimal(value)
    if d is None:
        return '—'
    text = f'{abs(d):,.2f}'
    sign = '-' if d < 0 and text.strip('0.,') else '+'
    return f'{sign}{text}%'


@register.filter
def usd_compact(value):
    """Капитализация: $1.23T / $456.70B / $12.30M"""
    d = _to_decimal(value)
    if d is None:
        return '—'
    a = abs(d)
    for limit, suffix in ((Decimal('1e12'), 'T'), (Decimal('1e9'), 'B'), (Decimal('1e6'), 'M')):
        if a >= limit:
            return f'${a / limit:,.2f}{suffix}'
    return f'${a:,.0f}'


@register.filter
def trim_zeros(value):
    """0.00500000 -> 0.005"""
    d = _to_decimal(value)
    if d is None:
        return '—'
    return format(d.normalize(), 'f')