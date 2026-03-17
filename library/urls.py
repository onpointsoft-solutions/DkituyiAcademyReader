from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import LibraryViewSet, UserLibraryViewSet, UserStatsViewSet, UserRecentBooksViewSet, UserReadingProgressViewSet

router = SimpleRouter()
router.register(r'', LibraryViewSet, basename='library')

user_router = SimpleRouter()
user_router.register(r'library', UserLibraryViewSet, basename='user-library')
user_router.register(r'stats', UserStatsViewSet, basename='user-stats')
user_router.register(r'recent-books', UserRecentBooksViewSet, basename='user-recent-books')
user_router.register(r'reading-progress', UserReadingProgressViewSet, basename='user-reading-progress')

urlpatterns = [
    path('', include(router.urls)),
    path('user/', include(user_router.urls)),
]
