from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ReaderViewSet

router = SimpleRouter()
router.register(r'', ReaderViewSet, basename='reader')

urlpatterns = [
    path('', include(router.urls)),
]
