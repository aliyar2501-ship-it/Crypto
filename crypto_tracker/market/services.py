import requests

class CoinGeckoService:
    """Сервис для работы с бесплатным API CoinGecko."""
    BASE_URL = "https://api.coingecko.com/api/v3"

    @classmethod
    def get_top_coins(cls, per_page=100):
        """Получает список популярных монет с актуальными ценами."""
        url = f"{cls.BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h"
        }
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            # Если API лежит или нет интернета, возвращаем пустой список, чтобы сайт не падал
            return []
        return []

    @classmethod
    def get_live_prices(cls, coin_ids_list):
        """Получает текущие цены для конкретного списка ID монет."""
        if not coin_ids_list:
            return {}

        # Превращаем список ['bitcoin', 'ethereum'] в строку 'bitcoin,ethereum'
        ids_str = ",".join(coin_ids_list)
        url = f"{cls.BASE_URL}/simple/price"
        params = {
            "ids": ids_str,
            "vs_currencies": "usd"
        }
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                # Возвращает словарь вида: {'bitcoin': {'usd': 65000}, 'ethereum': {'usd': 3400}}
                return response.json()
        except requests.RequestException:
            return {}
        return {}