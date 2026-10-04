import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasBotSecret(BasePermission):
    """Пускает только запросы с верным заголовком X-Bot-Secret. Пустой секрет = доступ закрыт."""

    def has_permission(self, request, view):
        expected = settings.BOT_API_SECRET
        provided = request.headers.get('X-Bot-Secret', '')
        return bool(expected) and hmac.compare_digest(provided.encode(), expected.encode())