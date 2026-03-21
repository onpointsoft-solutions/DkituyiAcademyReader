from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ReaderViewSet
from .annotation_views import ReadingFeaturesViewSet
from .simple_views import SimpleReaderViewSet
from .pdf_reader_views import PDFReaderViewSet

router = SimpleRouter()
router.register(r'', ReaderViewSet, basename='reader')
router.register(r'features', ReadingFeaturesViewSet, basename='reading-features')
router.register(r'simple', SimpleReaderViewSet, basename='simple-reader')
router.register(r'pdf', PDFReaderViewSet, basename='pdf-reader')

urlpatterns = [
    path('', include(router.urls)),
]