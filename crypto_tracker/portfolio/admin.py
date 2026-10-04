from django.contrib import admin

from .models import Asset, UserProfile


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'amount', 'buy_price', 'user', 'created_at')
    list_select_related = ('user',)
    search_fields = ('symbol', 'name', 'user__username')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    raw_id_fields = ('user',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'telegram_id')       # secret_key в списке не показываем
    list_select_related = ('user',)
    search_fields = ('user__username', 'telegram_id')
    readonly_fields = ('secret_key',)
    raw_id_fields = ('user',)
    actions = ['reset_telegram']

    @admin.action(description='Сбросить привязку Telegram')
    def reset_telegram(self, request, queryset):
        count = queryset.update(telegram_id=None)
        self.message_user(request, f'Сброшено привязок: {count}')