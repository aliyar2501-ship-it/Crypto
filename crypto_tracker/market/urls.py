from django.urls import path
from .views import market_view

app_name = 'market'

urlpatterns = [
    path('', market_view, name='index'),
]