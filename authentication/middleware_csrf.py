from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse

class DisableCSRFMiddleware(MiddlewareMixin):
    """
    Middleware to disable CSRF protection for authentication, admin, user, payment, and reader endpoints
    """
    
    def process_request(self, request):
        # Disable CSRF for authentication, admin, user, payment, reader, and books endpoints
        if (request.path.startswith('/api/auth/') or 
            request.path.startswith('/api/admin/') or 
            request.path.startswith('/api/user/') or 
            request.path.startswith('/api/payments/') or 
            request.path.startswith('/api/reader/') or
            request.path.startswith('/api/books/')):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
    
    def process_response(self, request, response):
        # Add CORS headers for authentication, admin, user, payment, reader, and books endpoints
        if (request.path.startswith('/api/auth/') or 
            request.path.startswith('/api/admin/') or 
            request.path.startswith('/api/user/') or 
            request.path.startswith('/api/payments/') or 
            request.path.startswith('/api/reader/') or
            request.path.startswith('/api/books/')):
            
            # Handle preflight requests
            if request.method == 'OPTIONS':
                response = HttpResponse(status=204)
                response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
                response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
                response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Accept-Ranges, Range'
                response['Access-Control-Allow-Credentials'] = 'true'
                response['Access-Control-Max-Age'] = '86400'
                return response
            
            # Add CORS headers for actual requests
            response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Accept-Ranges, Range'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'
            
        return response
