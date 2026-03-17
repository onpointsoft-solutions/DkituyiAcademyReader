from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.serializers import Serializer
import jwt
from django.conf import settings


class UserSerializer(Serializer):
    def __init__(self, instance=None, data=None, **kwargs):
        super().__init__(instance, data, **kwargs)
    
    def to_representation(self, instance):
        return {
            'id': instance.id,
            'username': instance.username,
            'email': instance.email,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
        }


@method_decorator(csrf_exempt, name='dispatch')
class DjangoLoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Django login endpoint"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        print(f"🔍 DEBUG: Login attempt - Username: {username}")
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Generate JWT token
            jwt_payload = {
                'user_id': user.id,
                'user_email': user.email,
                'username': user.username,
                'exp': timezone.now() + timezone.timedelta(days=7),  # 7 days expiry
                'iat': timezone.now()
            }
            
            jwt_token = jwt.encode(
                jwt_payload,
                settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM
            )
            
            # Return user data and JWT token
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff,
            }
            
            print(f"🔍 DEBUG: Login successful - User data: {user_data}")
            print(f"🔍 DEBUG: Is SuperUser: {user.is_superuser}")
            print(f"🔍 DEBUG: Is Staff: {user.is_staff}")
            print(f"🔍 DEBUG: JWT Token generated: {jwt_token[:20]}...")
            
            return Response({
                'message': 'Login successful',
                'user': user_data,
                'token': jwt_token
            })
        else:
            print(f"🔍 DEBUG: Login failed - Invalid credentials for {username}")
            return Response(
                {'error': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )


@method_decorator(csrf_exempt, name='dispatch')
class DjangoRegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Django registration endpoint"""
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        if not username or not email or not password:
            return Response(
                {'error': 'Username, email, and password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Email already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Auto-login after registration
        login(request, user)
        
        # Return user data manually
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
        }
        
        return Response({
            'message': 'Registration successful',
            'user': user_data
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class DjangoLogoutView(APIView):
    def post(self, request):
        """Django logout endpoint"""
        logout(request)
        return Response({'message': 'Logout successful'})


class DjangoUserInfoView(APIView):
    def get(self, request):
        """Get current user info"""
        if request.user.is_authenticated:
            user_data = {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }
            return Response({
                'user': user_data,
                'is_authenticated': True
            })
        else:
            return Response({
                'user': None,
                'is_authenticated': False
            }, status=status.HTTP_401_UNAUTHORIZED)
