from django.urls import path
from . import views
from . import views_django

urlpatterns = [
    # CSRF token endpoint
    path('csrf/', views_django.get_csrf_token, name='get-csrf-token'),
    
    # JWT endpoints (for WordPress integration)
    path('verify/', views.verify_token, name='verify-token'),
    path('user/', views.user_info, name='user-info'),
    
    # WordPress JWT integration endpoints
    path('wordpress-login/', views.wordpress_login, name='wordpress-login'),
    path('verify-wordpress-token/', views.verify_wordpress_token, name='verify-wordpress-token'),
    path('status/', views.auth_status, name='auth-status'),
    
    # Django authentication endpoints
    path('login/', views_django.DjangoLoginView.as_view(), name='django-login'),
    path('register/', views_django.DjangoRegisterView.as_view(), name='django-register'),
    path('logout/', views_django.DjangoLogoutView.as_view(), name='django-logout'),
    path('me/', views_django.DjangoUserInfoView.as_view(), name='django-user-info'),
]
