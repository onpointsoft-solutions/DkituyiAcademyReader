from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'books', views.AdminBookViewSet, basename='admin-book')

urlpatterns = [
    path('stats/', views.AdminStatsView.as_view()),
    path('users/', views.AdminUserListView.as_view()),
    path('reports/', views.AdminReportsView.as_view()),
    path('', include(router.urls)),
]
