from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'books', views.AdminBookViewSet, basename='admin-book')

urlpatterns = [
    path('stats/', views.AdminStatsView.as_view()),
    path('users/', views.AdminUserListView.as_view()),
    path('books/', views.AdminBookListView.as_view()),
    path('progress/', views.AdminUserProgressView.as_view()),
    path('reports/', views.AdminReportsView.as_view()),
    path('system-health/', views.AdminSystemHealthView.as_view()),
    path('recent-activity/', views.AdminRecentActivityView.as_view()),
    path('', include(router.urls)),
]
