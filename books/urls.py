from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import BookViewSet
from .preview_views import BookPreviewViewSet

router = SimpleRouter()
router.register(r'', BookViewSet, basename='book')
router.register(r'preview', BookPreviewViewSet, basename='book-preview')

urlpatterns = [
    path('', include(router.urls)),
]
