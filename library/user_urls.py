from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import UserLibraryViewSet, UserStatsViewSet, UserRecentBooksViewSet, UserReadingProgressViewSet

router = SimpleRouter()
router.register(r'library', UserLibraryViewSet, basename='user-library')
router.register(r'stats', UserStatsViewSet, basename='user-stats')
router.register(r'recent-books', UserRecentBooksViewSet, basename='user-recent-books')
router.register(r'reading-progress', UserReadingProgressViewSet, basename='user-reading-progress')

urlpatterns = [
    path('', include(router.urls)),
]
