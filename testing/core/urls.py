from django.urls import path
from . import views

urlpatterns = [
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('settings/', views.settings_view, name='settings_view'),
    path('update_preferences/', views.update_preferences, name='update_preferences'),
]
