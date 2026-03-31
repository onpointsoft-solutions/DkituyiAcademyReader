"""
User API URL Configuration

This module defines URL patterns for user-related API endpoints.
Uses class-based views for better organization and maintainability.
"""

from django.urls import path
from . import views

app_name = 'user_api'

urlpatterns = [
    # Class-based view endpoints (recommended)
    path('stats/', views.UserStatsView.as_view(), name='user_stats'),
    path('recent-books/', views.RecentBooksView.as_view(), name='recent_books'),
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('reading-progress/', views.ReadingProgressView.as_view(), name='update_reading_progress'),
    
    # Function-based view endpoints (deprecated - for backward compatibility)
    # These will be removed in future versions
    # path('stats/legacy/', views.user_stats, name='user_stats_legacy'),
    # path('recent-books/legacy/', views.recent_books, name='recent_books_legacy'),
    # path('profile/legacy/', views.user_profile, name='user_profile_legacy'),
    # path('reading-progress/legacy/', views.update_reading_progress, name='update_reading_progress_legacy'),
]
