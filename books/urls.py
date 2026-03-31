from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import BookViewSet, PDFStreamingView, BookProgressView, PublicBookViewSet, test_public_books, PDFMetadataExtractionView
from .preview_views import BookPreviewViewSet

# Authenticated books router
router = SimpleRouter()
router.register(r'', BookViewSet, basename='book')
router.register(r'preview', BookPreviewViewSet, basename='book-preview')

# Public books router (no authentication required)
public_router = SimpleRouter()
public_router.register(r'public', PublicBookViewSet, basename='public-book')

urlpatterns = [
    path('test/', test_public_books, name='test-public-books'),
    path('extract-metadata/', PDFMetadataExtractionView.as_view(), name='pdf-metadata-extraction'),
    path('', include(router.urls)),
    path('', include(public_router.urls)),
    path('<int:book_id>/pdf/', PDFStreamingView.as_view(), name='book-pdf'),
    path('<int:book_id>/progress/', BookProgressView.as_view(), name='book-progress'),
]
