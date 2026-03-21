import jwt
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(MiddlewareMixin):
    """
    Middleware to extract and verify JWT from Authorization header
    Supports both Django JWT and WordPress JWT tokens
    """
    
    def process_request(self, request):
        # Skip authentication for certain paths
        skip_paths = ['/admin/', '/api/auth/login/', '/api/auth/register/', '/api/auth/logout/', '/api/auth/me/', '/api/auth/wordpress-login/', '/api/reader/features/', '/api/reader/features/start_reading_session/', '/api/reader/features/get_annotations/', '/api/reader/features/add_bookmark/', '/api/reader/features/add_highlight/', '/api/reader/features/add_note/', '/api/reader/features/update_highlight/', '/api/reader/features/update_note/', '/api/reader/features/delete_bookmark/', '/api/reader/features/delete_highlight/', '/api/reader/features/delete_note/', '/api/reader/features/end_reading_session/', '/api/reader/features/report_screenshot_attempt/', '/api/reader/pdf/', '/api/reader/pdf/update_progress/']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
            
        # Debug logging for user and admin endpoints
        if request.path.startswith('/api/user/') or request.path.startswith('/api/admin/'):
            logger.info(f"🔍 {'User' if request.path.startswith('/api/user/') else 'Admin'} endpoint accessed: {request.path}")
            logger.info(f"🔍 Authorization header: {request.headers.get('Authorization')}")
            
        # First check for Django session auth
        if hasattr(request, 'user') and request.user.is_authenticated:
            request.user_payload = {
                'user_id': request.user.id,
                'user_email': request.user.email
            }
            return None
            
        # Then check for JWT token
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            try:
                # Decode and verify JWT
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM]
                )
                
                # Debug logging
                if request.path.startswith('/api/user/') or request.path.startswith('/api/admin/'):
                    print(f"DEBUG: JWT decoded successfully: {payload}")
                
                # Attach user payload to request
                request.user_payload = payload
                request.user = type('User', (), {
                    'id': payload.get('user_id'),
                    'email': payload.get('user_email'),
                    'username': payload.get('username'),
                    'is_authenticated': True,
                    'is_staff': False,  # Will be checked in permission class
                    'is_superuser': False  # Will be checked in permission class
                })()
                
                if request.path.startswith('/api/admin/'):
                    print(f"DEBUG: JWT middleware set user object for admin endpoint")
                    print(f"DEBUG: User object - id: {request.user.id}, email: {request.user.email}, authenticated: {request.user.is_authenticated}")
                
            except jwt.ExpiredSignatureError:
                if request.path.startswith('/api/user/') or request.path.startswith('/api/admin/'):
                    print(f"DEBUG: JWT token expired")
                return JsonResponse({'error': 'Token has expired'}, status=401)
            except jwt.InvalidTokenError:
                if request.path.startswith('/api/user/') or request.path.startswith('/api/admin/'):
                    print(f"DEBUG: Invalid JWT token")
                return JsonResponse({'error': 'Invalid token'}, status=401)
            except Exception as e:
                if request.path.startswith('/api/user/') or request.path.startswith('/api/admin/'):
                    print(f"DEBUG: JWT decode error: {str(e)}")
                return JsonResponse({'error': 'Authentication failed'}, status=401)
        else:
            # No token provided
            if request.path.startswith('/api/user/') or request.path.startswith('/api/admin/'):
                print(f"DEBUG: No JWT token provided")
            request.user_payload = None
            request.user = AnonymousUser()
            
        return None
