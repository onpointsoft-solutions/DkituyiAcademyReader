from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse


class DisableCSRFMiddleware(MiddlewareMixin):
    """
    Middleware to disable CSRF protection for authentication, admin, user, and payment endpoints
    """
    
    def process_request(self, request):
        # Disable CSRF for authentication, admin, user, and payment endpoints
        if (request.path.startswith('/api/auth/') or 
            request.path.startswith('/api/admin/') or 
            request.path.startswith('/api/user/') or
            request.path.startswith('/api/payments/')):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
    
    def process_response(self, request, response):
        # Add CORS headers for authentication, admin, user, and payment endpoints
        if (request.path.startswith('/api/auth/') or 
            request.path.startswith('/api/admin/') or 
            request.path.startswith('/api/user/') or
            request.path.startswith('/api/payments/')):
            response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response['Access-Control-Allow-Credentials'] = 'true'
        return response
