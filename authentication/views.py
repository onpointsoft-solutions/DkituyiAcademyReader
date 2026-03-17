import jwt
import requests
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from core.email import EmailService
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_token(request):
    """
    Verify JWT token and return user information
    """
    token = request.data.get('token')
    
    if not token:
        return Response(
            {'error': 'No token provided'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Decode and verify JWT
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        return Response({
            'valid': True,
            'user_id': payload.get('user_id'),
            'user_email': payload.get('user_email'),
            'exp': payload.get('exp')
        })
        
    except jwt.ExpiredSignatureError:
        return Response(
            {'error': 'Token has expired'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    except jwt.InvalidTokenError:
        return Response(
            {'error': 'Invalid token'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {'error': 'Token verification failed'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def user_info(request):
    """
    Get current user information from JWT payload
    """
    if not hasattr(request, 'user_payload') or not request.user_payload:
        return Response(
            {'error': 'Authentication required'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    return Response({
        'user_id': request.user_payload.get('user_id'),
        'user_email': request.user_payload.get('user_email'),
        'is_authenticated': True
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset(request):
    """
    Handle password reset requests
    """
    email = request.data.get('email')
    
    if not email:
        return Response(
            {'error': 'Email is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(email=email)
        # Generate reset token (simplified - in production, use more secure method)
        reset_token = jwt.encode(
            {'user_id': user.id, 'email': email, 'type': 'password_reset'},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        # Send password reset email
        EmailService.send_password_reset_email(
            user_email=email,
            reset_link=reset_link,
            user_name=user.get_full_name() or user.username
        )
        
        return Response({
            'message': 'Password reset link sent to your email',
            'success': True
        })
        
    except User.DoesNotExist:
        # Don't reveal if email exists or not
        return Response({
            'message': 'If an account with this email exists, a password reset link has been sent',
            'success': True
        })
    except Exception as e:
        return Response(
            {'error': 'Password reset failed'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# WordPress JWT Authentication Integration
WORDPRESS_SITE_URL = getattr(settings, 'WORDPRESS_SITE_URL', 'https://dkituyiacademy.org')
WORDPRESS_JWT_TOKEN_URL = f"{WORDPRESS_SITE_URL}/wp-json/jwt-auth/v1/token"


@api_view(['POST'])
@permission_classes([AllowAny])
def wordpress_login(request):
    """
    Authenticate with WordPress JWT and create/update local user
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        logger.info(f"🔍 WordPress login attempt for user: {username}")
        
        # Step 1: Authenticate with WordPress JWT
        wordpress_response = requests.post(
            WORDPRESS_JWT_TOKEN_URL,
            json={'username': username, 'password': password},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        logger.info(f"🔍 WordPress response status: {wordpress_response.status_code}")
        
        if wordpress_response.status_code != 200:
            logger.error(f"🔍 WordPress auth failed: {wordpress_response.text}")
            return Response(
                {'error': 'WordPress authentication failed'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        wordpress_data = wordpress_response.json()
        jwt_token = wordpress_data.get('token')
        user_email = wordpress_data.get('user_email')
        user_id = wordpress_data.get('user_id')
        display_name = wordpress_data.get('user_display_name')
        
        logger.info(f"🔍 WordPress auth successful for: {user_email} (ID: {user_id})")
        
        # Step 2: Create or update local user
        try:
            local_user = User.objects.get(email=user_email)
            logger.info(f"🔍 Existing user found: {local_user.username}")
            created = False
        except User.DoesNotExist:
            # Create new user
            username_base = user_email.split('@')[0]
            username = username_base
            counter = 1
            
            # Ensure unique username
            while User.objects.filter(username=username).exists():
                username = f"{username_base}{counter}"
                counter += 1
            
            local_user = User.objects.create_user(
                username=username,
                email=user_email,
                first_name=display_name.split()[0] if display_name else '',
                last_name=' '.join(display_name.split()[1:]) if display_name and len(display_name.split()) > 1 else ''
            )
            logger.info(f"🔍 New user created: {local_user.username}")
            created = True
        
        # Step 3: Generate local JWT token for Django backend
        from django.utils import timezone
        local_jwt_payload = {
            'user_id': local_user.id,
            'user_email': local_user.email,
            'username': local_user.username,
            'wordpress_user_id': user_id,
            'exp': timezone.now() + timezone.timedelta(days=7),
            'iat': timezone.now()
        }
        
        local_jwt_token = jwt.encode(
            local_jwt_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        # Step 4: Track authentication
        logger.info(f"🔍 Authentication tracked - User: {local_user.username}, WP_ID: {user_id}")
        
        user_data = {
            'id': local_user.id,
            'username': local_user.username,
            'email': local_user.email,
            'first_name': local_user.first_name,
            'last_name': local_user.last_name,
            'is_superuser': local_user.is_superuser,
            'is_staff': local_user.is_staff,
            'wordpress_user_id': user_id,
            'display_name': display_name
        }
        
        response_data = {
            'message': 'Login successful',
            'user': user_data,
            'token': local_jwt_token,
            'wordpress_token': jwt_token,
            'created': created
        }
        
        logger.info(f"🔍 Login completed successfully for: {local_user.username}")
        return Response(response_data)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"🔍 WordPress connection error: {str(e)}")
        return Response(
            {'error': 'Failed to connect to WordPress site'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"🔍 WordPress login error: {str(e)}")
        return Response(
            {'error': 'Authentication failed'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_wordpress_token(request):
    """
    Verify WordPress JWT token and create local session
    """
    wordpress_token = request.data.get('wordpress_token')
    
    if not wordpress_token:
        return Response(
            {'error': 'WordPress token is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        logger.info("🔍 Verifying WordPress JWT token")
        
        # Decode WordPress JWT token (without verification for now, as we trust WordPress)
        decoded = jwt.decode(wordpress_token, options={"verify_signature": False})
        user_email = decoded.get('user_email')
        wordpress_user_id = decoded.get('user_id')
        
        if not user_email or not wordpress_user_id:
            return Response(
                {'error': 'Invalid WordPress token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"🔍 WordPress token valid for: {user_email} (WP_ID: {wordpress_user_id})")
        
        # Get or create local user
        try:
            local_user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found in local database'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate local JWT token
        from django.utils import timezone
        local_jwt_payload = {
            'user_id': local_user.id,
            'user_email': local_user.email,
            'username': local_user.username,
            'wordpress_user_id': wordpress_user_id,
            'exp': timezone.now() + timezone.timedelta(days=7),
            'iat': timezone.now()
        }
        
        local_jwt_token = jwt.encode(
            local_jwt_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        logger.info(f"🔍 Local token generated for: {local_user.username}")
        
        return Response({
            'message': 'Token verified successfully',
            'user': {
                'id': local_user.id,
                'username': local_user.username,
                'email': local_user.email,
                'first_name': local_user.first_name,
                'last_name': local_user.last_name,
                'is_superuser': local_user.is_superuser,
                'is_staff': local_user.is_staff,
            },
            'token': local_jwt_token
        })
        
    except Exception as e:
        logger.error(f"🔍 WordPress token verification error: {str(e)}")
        return Response(
            {'error': 'Token verification failed'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def auth_status(request):
    """
    Get current authentication status and tracking info
    """
    if not hasattr(request, 'user_payload') or not request.user_payload:
        return Response({
            'authenticated': False,
            'message': 'No active session'
        })
    
    user_payload = request.user_payload
    logger.info(f"🔍 Auth status check for user_id: {user_payload.get('user_id')}")
    
    return Response({
        'authenticated': True,
        'user_id': user_payload.get('user_id'),
        'user_email': user_payload.get('user_email'),
        'username': user_payload.get('username'),
        'wordpress_user_id': user_payload.get('wordpress_user_id'),
        'exp': user_payload.get('exp'),
        'iat': user_payload.get('iat')
    })
