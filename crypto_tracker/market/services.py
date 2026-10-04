import hashlib
import logging

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CoinGeckoError(Exception):
    """CoinGecko недоступен (сеть, лимиты, 5xx)."""


class CoinGeckoService:
    BASE_URL = "https://api.coingecko.com/api/v3"
    TIMEOUT = 8
    TOP_COINS_TTL = 60
    PRICES_TTL = 60
    COIN_INFO_TTL = 60 * 60 * 24

    @classmethod
    def _get(cls, path, params):
        """JSON-ответ или None при любой ошибке (ошибка пишется в лог)."""
        try:
            response = requests.get(f"{cls.BASE_URL}{path}", params=params, timeout=cls.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("CoinGecko %s failed: %s", path, exc)
            return None

    @classmethod
    def get_top_coins(cls, per_page=100):
        """Список монет или None, если API недоступен."""
        key = f"cg:top:{per_page}"
        data = cache.get(key)
        if data is None:
            data = cls._get("/coins/markets", {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
            })
            if not isinstance(data, list):
                return None
            cache.set(key, data, cls.TOP_COINS_TTL)
        return data

    @classmethod
    def get_live_prices(cls, coin_ids):
        """{'bitcoin': {'usd': 65000}} или None, если API недоступен. Пустой вход -> {}."""
        ids = sorted({c for c in coin_ids if c})
        if not ids:
            return {}
        digest = hashlib.md5(",".join(ids).encode(), usedforsecurity=False).hexdigest()
        key = f"cg:prices:{digest}"
        data = cache.get(key)
        if data is None:
            data = cls._get("/simple/price", {"ids": ",".join(ids), "vs_currencies": "usd"})
            if not isinstance(data, dict):
                return None
            cache.set(key, data, cls.PRICES_TTL)
        return data

    @classmethod
    def get_coin(cls, coin_id):
        """
        {'id', 'symbol', 'name'}; None — такой монеты нет;
        CoinGeckoError — не удалось проверить (API недоступен).
        """
        key = f"cg:coin:{coin_id}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        try:
            response = requests.get(
                f"{cls.BASE_URL}/coins/{coin_id}",
                params={"localization": "false", "tickers": "false", "market_data": "false",
                        "community_data": "false", "developer_data": "false", "sparkline": "false"},
                timeout=cls.TIMEOUT,
            )
        except requests.RequestException as exc:
            raise CoinGeckoError(str(exc)) from exc

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise CoinGeckoError(f"HTTP {response.status_code}")
        try:
            raw = response.json()
            info = {"id": raw["id"], "symbol": raw["symbol"].upper(), "name": raw["name"]}
        except (ValueError, KeyError) as exc:
            raise CoinGeckoError("bad response") from exc
        cache.set(key, info, cls.COIN_INFO_TTL)
        return info