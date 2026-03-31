from django.urls import path
from . import views

app_name = 'user_api'

urlpatterns = [
    path('stats/', views.user_stats, name='user_stats'),
    path('recent-books/', views.recent_books, name='recent_books'),
    path('profile/', views.user_profile, name='user_profile'),
    path('reading-progress/', views.update_reading_progress, name='update_reading_progress'),
]
