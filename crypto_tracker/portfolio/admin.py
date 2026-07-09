from django.contrib import admin
from .models import Asset, UserProfile

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'amount', 'buy_price', 'user', 'created_at')
    search_fields = ('symbol', 'name', 'user__username')
    list_filter = ('symbol', 'created_at')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'telegram_id', 'secret_key')
    search_fields = ('user__username', 'telegram_id')