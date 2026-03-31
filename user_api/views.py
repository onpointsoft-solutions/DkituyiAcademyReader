"""
User API Views - Production-ready endpoints for user dashboard and profile functionality.

This module provides clean, secure, and performant API endpoints for:
- User statistics and reading progress
- Recent books and library management
- User profile management
- Reading progress tracking

All endpoints follow consistent JSON response format and proper error handling.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Max, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from library.models import UserLibrary, ReadingProgress
from books.models import Book

logger = logging.getLogger(__name__)
User = get_user_model()


class BaseAPIView(APIView):
    """
    Base API view with common functionality for all user API endpoints.
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def success_response(data: Any = None, message: str = "Success", status_code: int = status.HTTP_200_OK) -> Response:
        """Standard success response format."""
        response_data = {
            "success": True,
            "message": message,
            "data": data
        }
        return Response(response_data, status=status_code)

    @staticmethod
    def error_response(message: str, status_code: int = status.HTTP_400_BAD_REQUEST, data: Any = None) -> Response:
        """Standard error response format."""
        response_data = {
            "success": False,
            "message": message,
            "data": data
        }
        return Response(response_data, status=status_code)

    def get_user_context(self) -> Dict[str, Any]:
        """Get user context for logging and processing."""
        return {
            "user_id": self.request.user.id,
            "username": self.request.user.username,
            "ip_address": self.get_client_ip()
        }

    def get_client_ip(self) -> str:
        """Get client IP address for logging."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return self.request.META.get('REMOTE_ADDR', 'unknown')


class UserStatsView(BaseAPIView):
    """
    Retrieve user reading statistics for dashboard display.
    
    Returns comprehensive reading metrics including:
    - Total books in library
    - Books completed
    - Reading time estimation
    - Reading streak
    - Achievement count
    """
    
    def get(self, request) -> Response:
        """Get user statistics."""
        user_context = self.get_user_context()
        
        try:
            # Optimized queries with select_related and prefetch_related
            library_stats = UserLibrary.objects.filter(
                user=request.user, 
                is_active=True
            ).aggregate(
                total_books=Count('id'),
                total_pages=Sum('book__pages')
            )
            
            # Get reading progress with optimized query
            progress_stats = ReadingProgress.objects.filter(
                user=request.user
            ).aggregate(
                books_completed=Count('id', filter=Q(progress_percentage=100)),
                total_pages_read=Sum('current_page'),
                last_activity=Max('updated_at')
            )
            
            # Calculate reading time (2 minutes per page assumption)
            total_pages_read = progress_stats['total_pages_read'] or 0
            reading_hours = round(total_pages_read * 2 / 60, 1)
            
            # Calculate reading streak
            reading_streak = self._calculate_reading_streak(request.user)
            
            # Calculate achievements based on milestones
            achievements = self._calculate_achievements(
                progress_stats['books_completed'] or 0,
                reading_streak
            )
            
            stats_data = {
                'totalBooks': library_stats['total_books'] or 0,
                'booksRead': progress_stats['books_completed'] or 0,
                'readingTimeHours': reading_hours,
                'readingStreak': reading_streak,
                'achievements': achievements,
                'totalPages': library_stats['total_pages'] or 0,
                'lastActivity': progress_stats['last_activity']
            }
            
            logger.info(
                "User statistics retrieved successfully",
                extra={
                    "user_id": user_context["user_id"],
                    "username": user_context["username"],
                    "stats": stats_data
                }
            )
            
            return self.success_response(stats_data, "Statistics retrieved successfully")
            
        except Exception as e:
            logger.error(
                "Failed to retrieve user statistics",
                extra={
                    "user_id": user_context["user_id"],
                    "username": user_context["username"],
                    "error": str(e)
                },
                exc_info=True
            )
            return self.error_response("Failed to retrieve statistics", status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _calculate_reading_streak(self, user) -> int:
        """Calculate current reading streak in days."""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Get unique days with reading activity
        activity_days = ReadingProgress.objects.filter(
            user=user,
            updated_at__gte=thirty_days_ago
        ).dates('updated_at', 'day')
        
        if not activity_days.exists():
            return 0
        
        # Convert to list and sort
        days_list = list(activity_days)
        days_list.sort(reverse=True)
        
        # Calculate streak
        streak = 1
        for i in range(1, len(days_list)):
            if (days_list[i-1] - days_list[i]).days == 1:
                streak += 1
            else:
                break
        
        return streak

    def _calculate_achievements(self, books_completed: int, reading_streak: int) -> int:
        """Calculate achievement count based on milestones."""
        achievements = 0
        
        # Book-based achievements
        if books_completed >= 1:
            achievements += 1
        if books_completed >= 5:
            achievements += 1
        if books_completed >= 10:
            achievements += 1
        if books_completed >= 25:
            achievements += 1
        if books_completed >= 50:
            achievements += 1
        
        # Streak-based achievements
        if reading_streak >= 7:
            achievements += 1
        if reading_streak >= 30:
            achievements += 1
        if reading_streak >= 100:
            achievements += 1
        
        return achievements


class RecentBooksView(BaseAPIView):
    """
    Retrieve user's recent books with reading progress.
    
    Returns the most recently accessed books from the user's library
    with current reading progress and book details.
    """
    
    def get(self, request) -> Response:
        """Get recent books with progress."""
        user_context = self.get_user_context()
        
        try:
            # Optimized query with select_related and prefetch_related
            library_entries = UserLibrary.objects.filter(
                user=request.user, 
                is_active=True
            ).select_related(
                'book',
                'book__author'
            ).prefetch_related(
                'book__categories'
            ).order_by('-updated_at')[:20]  # Limit for performance
            
            # Get reading progress for these books in bulk
            book_ids = [entry.book.id for entry in library_entries]
            progress_map = {
                progress.book_id: progress
                for progress in ReadingProgress.objects.filter(
                    user=request.user,
                    book_id__in=book_ids
                )
            }
            
            # Build response data
            recent_books = []
            for entry in library_entries:
                book = entry.book
                progress = progress_map.get(book.id)
                
                book_data = {
                    'id': book.id,
                    'title': book.title,
                    'subtitle': book.subtitle or '',
                    'author_name': book.author.name if book.author else 'Unknown Author',
                    'cover_url': book.cover_url or '',
                    'cover_display_url': book.cover_image.url if book.cover_image else book.cover_url or '',
                    'pages': book.pages or 0,
                    'language': book.language or 'en',
                    'categories': [cat.name for cat in book.categories.all()],
                    'reading_progress': progress.progress_percentage if progress else 0,
                    'current_page': progress.current_page if progress else 0,
                    'total_pages': book.pages or 0,
                    'last_read': progress.updated_at if progress else entry.created_at,
                    'is_completed': progress.progress_percentage >= 100 if progress else False,
                    'price': float(book.price) if book.price else 0.0,
                    'is_free': book.is_free
                }
                
                recent_books.append(book_data)
            
            logger.info(
                "Recent books retrieved successfully",
                extra={
                    "user_id": user_context["user_id"],
                    "username": user_context["username"],
                    "book_count": len(recent_books)
                }
            )
            
            return self.success_response(
                {
                    'results': recent_books[:10],  # Return top 10
                    'count': len(recent_books)
                },
                "Recent books retrieved successfully"
            )
            
        except Exception as e:
            logger.error(
                "Failed to retrieve recent books",
                extra={
                    "user_id": user_context["user_id"],
                    "username": user_context["username"],
                    "error": str(e)
                },
                exc_info=True
            )
            return self.error_response("Failed to retrieve recent books", status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileView(BaseAPIView):
    """
    Get or update user profile information.
    
    Handles profile retrieval and updates with proper validation
    and security measures.
    """
    
    def get(self, request) -> Response:
        """Get user profile with statistics."""
        user_context = self.get_user_context()
        
        try:
            # Get user statistics
            library_count = UserLibrary.objects.filter(
                user=request.user, 
                is_active=True
            ).count()
            
            progress_stats = ReadingProgress.objects.filter(
                user=request.user
            ).aggregate(
                books_completed=Count('id', filter=Q(progress_percentage=100)),
                total_pages_read=Sum('current_page')
            )
            
            # Calculate derived metrics
            total_pages_read = progress_stats['total_pages_read'] or 0
            reading_hours = round(total_pages_read * 2 / 60, 1)
            
            # Get reading streak
            reading_streak = self._calculate_reading_streak(request.user)
            
            # Calculate achievements
            achievements = self._calculate_achievements(
                progress_stats['books_completed'] or 0,
                reading_streak
            )
            
            # Build profile data
            profile_data = {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name or '',
                'last_name': request.user.last_name or '',
                'date_joined': request.user.date_joined,
                'is_staff': request.user.is_staff,
                'is_active': request.user.is_active,
                'library_count': library_count,
                'books_read': progress_stats['books_completed'] or 0,
                'reading_hours': reading_hours,
                'reading_streak': reading_streak,
                'achievements': achievements,
                'last_login': request.user.last_login
            }
            
            # Add custom profile fields if they exist
            custom_fields = ['bio', 'avatar', 'favorite_genres', 'reading_goal']
            for field in custom_fields:
                if hasattr(request.user, field):
                    profile_data[field] = getattr(request.user, field)
                else:
                    profile_data[field] = '' if field != 'reading_goal' else 2
            
            logger.info(
                "User profile retrieved successfully",
                extra={
                    "user_id": user_context["user_id"],
                    "username": user_context["username"]
                }
            )
            
            return self.success_response(profile_data, "Profile retrieved successfully")
            
        except Exception as e:
            logger.error(
                "Failed to retrieve user profile",
                extra={
                    "user_id": user_context["user_id"],
                    "username": user_context["username"],
                    "error": str(e)
                },
                exc_info=True
            )
            return self.error_response("Failed to retrieve profile", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request) -> Response:
        """Update user profile."""
        user_context = self.get_user_context()
        
        try:
            data = request.data
            
            # Validate required fields
            if 'username' in data and not data['username'].strip():
                return self.error_response("Username cannot be empty", status.HTTP_400_BAD_REQUEST)
            
            if 'email' in data and not data['email'].strip():
                return self.error_response("Email cannot be empty", status.HTTP_400_BAD_REQUEST)
            
            # Update basic fields
            updatable_fields = ['first_name', 'last_name', 'email']
            for field in updatable_fields:
                if field in data:
                    setattr(request.user, field, data[field].strip())
            
            # Update username if provided and different
            if 'username' in data and data['username'] != request.user.username:
                new_username = data['username'].strip()
                
                # Check if username is already taken
                if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
                    return self.error_response("Username is already taken", status.HTTP_400_BAD_REQUEST)
                
                request.user.username = new_username
            
            # Update custom profile fields if they exist
            custom_fields = ['bio', 'favorite_genres', 'reading_goal']
            for field in custom_fields:
                if field in data and hasattr(request.user, field):
                    if field == 'reading_goal':
                        try:
                            setattr(request.user, field, int(data[field]))
                        except (ValueError, TypeError):
                            return self.error_response(f"Invalid {field} value", status.HTTP_400_BAD_REQUEST)
                    else:
                        setattr(request.user, field, data[field].strip())
            
            request.user.save()
            
            logger.info(
                "User profile updated successfully",
                extra={
                    "user_id": user_context["user_id"],
                    "username": user_context["username"],
                    "updated_fields": list(data.keys())
                }
            )
            
            return self.success_response({"message": "Profile updated successfully"})
            
        except Exception as e:
            logger.error(
                "Failed to update user profile",
                extra={
                    "user_id": user_context["user_id"],
                    "username": user_context["username"],
                    "error": str(e)
                },
                exc_info=True
            )
            return self.error_response("Failed to update profile", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _calculate_reading_streak(self, user) -> int:
        """Calculate current reading streak in days."""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        activity_days = ReadingProgress.objects.filter(
            user=user,
            updated_at__gte=thirty_days_ago
        ).dates('updated_at', 'day')
        
        if not activity_days.exists():
            return 0
        
        days_list = list(activity_days)
        days_list.sort(reverse=True)
        
        streak = 1
        for i in range(1, len(days_list)):
            if (days_list[i-1] - days_list[i]).days == 1:
                streak += 1
            else:
                break
        
        return streak
    
    def _calculate_achievements(self, books_completed: int, reading_streak: int) -> int:
        """Calculate achievement count based on milestones."""
        achievements = 0
        
        if books_completed >= 1:
            achievements += 1
        if books_completed >= 5:
            achievements += 1
        if books_completed >= 10:
            achievements += 1
        if books_completed >= 25:
            achievements += 1
        if books_completed >= 50:
            achievements += 1
        
        if reading_streak >= 7:
            achievements += 1
        if reading_streak >= 30:
            achievements += 1
        if reading_streak >= 100:
            achievements += 1
        
        return achievements


class ReadingProgressView(BaseAPIView):
    """
    Update reading progress for a specific book.
    
    Handles progress updates with validation and security checks.
    """
    
    def post(self, request) -> Response:
        """Update reading progress for a book."""
        user_context = self.get_user_context()
        
        try:
            book_id = request.data.get('book_id')
            progress = request.data.get('progress', 0)
            current_page = request.data.get('current_page')
            
            # Validate required fields
            if not book_id:
                return self.error_response("Book ID is required", status.HTTP_400_BAD_REQUEST)
            
            # Validate progress range
            try:
                progress = float(progress)
                if not (0 <= progress <= 100):
                    return self.error_response("Progress must be between 0 and 100", status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return self.error_response("Invalid progress value", status.HTTP_400_BAD_REQUEST)
            
            # Validate book access
            library_entry = UserLibrary.objects.filter(
                user=request.user,
                book_id=book_id,
                is_active=True
            ).select_related('book').first()
            
            if not library_entry:
                return self.error_response("Book not found in your library", status.HTTP_404_NOT_FOUND)
            
            book = library_entry.book
            
            # Get or create reading progress
            reading_progress, created = ReadingProgress.objects.get_or_create(
                user=request.user,
                book=book,
                defaults={
                    'current_page': current_page or 1,
                    'total_pages': book.pages or 0,
                    'progress_percentage': progress
                }
            )
            
            if not created:
                reading_progress.current_page = current_page or reading_progress.current_page
                reading_progress.progress_percentage = progress
                reading_progress.save()
            
            logger.info(
                "Reading progress updated successfully",
                extra={
                    "user_id": user_context["user_id"],
                    "username": user_context["username"],
                    "book_id": book_id,
                    "progress": progress,
                    "current_page": reading_progress.current_page
                }
            )
            
            return self.success_response({
                "message": "Reading progress updated",
                "progress": reading_progress.progress_percentage,
                "current_page": reading_progress.current_page,
                "is_completed": reading_progress.progress_percentage >= 100
            }, "Progress updated successfully")
            
        except Exception as e:
            logger.error(
                "Failed to update reading progress",
                extra={
                    "user_id": user_context["user_id"],
                    "username": user_context["username"],
                    "error": str(e)
                },
                exc_info=True
            )
            return self.error_response("Failed to update reading progress", status.HTTP_500_INTERNAL_SERVER_ERROR)


# Function-based views for backward compatibility (deprecated)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    """Deprecated: Use UserStatsView.get() instead."""
    view = UserStatsView()
    view.request = request
    view.format_kwarg = None
    return view.get(request)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_books(request):
    """Deprecated: Use RecentBooksView.get() instead."""
    view = RecentBooksView()
    view.request = request
    view.format_kwarg = None
    return view.get(request)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Deprecated: Use UserProfileView.get() or UserProfileView.put() instead."""
    view = UserProfileView()
    view.request = request
    view.format_kwarg = None
    
    if request.method == 'GET':
        return view.get(request)
    elif request.method == 'PUT':
        return view.put(request)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_reading_progress(request):
    """Deprecated: Use ReadingProgressView.post() instead."""
    view = ReadingProgressView()
    view.request = request
    view.format_kwarg = None
    return view.post(request)
