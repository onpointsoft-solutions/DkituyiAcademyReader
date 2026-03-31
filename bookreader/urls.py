from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .admin import bookreader_admin
from payments.urls import payment_callback

urlpatterns = [
    path('admin/', admin.site.urls),
    path('superadmin/', bookreader_admin.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/admin/', include('admin_api.urls')),
    path('api/books/', include('books.urls')),
    path('api/library/', include('library.urls')),
    path('api/user/', include('user_api.urls')),  # Use dedicated user API
    path('api/payments/', include('payments.urls')),  # Add payments endpoints
    path('api/reader/', include('reader.urls')),
    path('payment/callback/', payment_callback, name='payment-callback'),  # Add callback route
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
