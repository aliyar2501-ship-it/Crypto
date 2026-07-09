from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('link-bot/', views.link_telegram, name='link_bot'),
    path('portfolio/', views.get_bot_portfolio, name='bot_portfolio'),
]