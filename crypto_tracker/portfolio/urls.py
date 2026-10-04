from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('', views.portfolio_list, name='list'),
    path('asset/new/', views.asset_create, name='create'),
    path('asset/<int:pk>/', views.asset_detail, name='detail'),
    path('asset/<int:pk>/edit/', views.asset_update, name='update'),
    path('asset/<int:pk>/delete/', views.asset_delete, name='delete'),
    path('profile/regenerate-key/', views.regenerate_key, name='regenerate_key'),
    path('profile/unlink-bot/', views.unlink_bot, name='unlink_bot'),
]

#portfolio urls.py