from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from library.models import UserLibrary, ReadingProgress
from books.models import Book
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    """Get user statistics for dashboard"""
    try:
        user = request.user
        
        # Get user's library
        library_entries = UserLibrary.objects.filter(user=user, is_active=True)
        total_books = library_entries.count()
        
        # Get reading progress
        progress_entries = ReadingProgress.objects.filter(user=user)
        books_read = progress_entries.filter(progress_percentage=100).count()
        
        # Calculate reading time (simplified - based on pages read)
        total_pages_read = sum(entry.current_page for entry in progress_entries)
        reading_hours = total_pages_read * 2  # Assume 2 minutes per page
        
        # Calculate reading streak (days with reading activity)
        reading_streak = 0
        today = datetime.now().date()
        
        # Get recent reading activity
        recent_activity = ReadingProgress.objects.filter(
            user=user,
            updated_at__gte=today - timedelta(days=30)
        ).order_by('-updated_at')
        
        if recent_activity.exists():
            # Simple streak calculation
            streak_days = set()
            for activity in recent_activity:
                streak_days.add(activity.updated_at.date())
            
            streak_days = sorted(streak_days, reverse=True)
            current_streak = 0
            
            for i, date in enumerate(streak_days):
                if i == 0:
                    current_streak = 1
                elif streak_days[i-1] - date == timedelta(days=1):
                    current_streak += 1
                else:
                    break
            
            reading_streak = current_streak
        
        # Calculate achievements (simplified)
        achievements = 0
        if books_read >= 1:
            achievements += 1
        if books_read >= 5:
            achievements += 1
        if books_read >= 10:
            achievements += 1
        if reading_streak >= 7:
            achievements += 1
        if reading_streak >= 30:
            achievements += 1
        
        stats = {
            'totalBooks': total_books,
            'booksRead': books_read,
            'readingTimeHours': reading_hours,
            'readingStreak': reading_streak,
            'achievements': achievements,
        }
        
        logger.info(f"📊 User stats for {user.username}: {stats}")
        return Response(stats)
        
    except Exception as e:
        logger.error(f"Error fetching user stats: {e}")
        return Response(
            {'error': 'Failed to fetch user statistics'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_books(request):
    """Get user's recent books with reading progress"""
    try:
        user = request.user
        
        # Get user's library entries with progress
        library_entries = UserLibrary.objects.filter(
            user=user, 
            is_active=True
        ).select_related('book').prefetch_related('book__author', 'book__categories')
        
        # Get reading progress for these books
        book_ids = [entry.book.id for entry in library_entries]
        progress_map = {}
        
        progress_entries = ReadingProgress.objects.filter(
            user=user, 
            book_id__in=book_ids
        )
        
        for progress in progress_entries:
            progress_map[progress.book_id] = progress
        
        # Build recent books data
        recent_books = []
        for entry in library_entries:
            book = entry.book
            progress = progress_map.get(book.id)
            
            book_data = {
                'id': book.id,
                'title': book.title,
                'subtitle': book.subtitle,
                'author_name': book.author.name if book.author else 'Unknown Author',
                'cover_url': book.cover_url,
                'cover_display_url': book.cover_image.url if book.cover_image else book.cover_url,
                'pages': book.pages,
                'language': book.language,
                'categories': [cat.name for cat in book.categories.all()],
                'reading_progress': progress.progress_percentage if progress else 0,
                'current_page': progress.current_page if progress else 0,
                'total_pages': book.pages,
                'last_read': progress.updated_at if progress else entry.created_at,
                'is_completed': progress.progress_percentage >= 100 if progress else False,
            }
            
            recent_books.append(book_data)
        
        # Sort by last read date
        recent_books.sort(key=lambda x: x['last_read'], reverse=True)
        
        logger.info(f"📚 Found {len(recent_books)} recent books for {user.username}")
        return Response({
            'results': recent_books[:10],  # Limit to 10 most recent
            'count': len(recent_books)
        })
        
    except Exception as e:
        logger.error(f"Error fetching recent books: {e}")
        return Response(
            {'error': 'Failed to fetch recent books'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get or update user profile"""
    try:
        user = request.user
        
        if request.method == 'GET':
            # Get user statistics for profile
            library_entries = UserLibrary.objects.filter(user=user, is_active=True)
            progress_entries = ReadingProgress.objects.filter(user=user)
            
            books_read = progress_entries.filter(progress_percentage=100).count()
            total_pages_read = sum(entry.current_page for entry in progress_entries)
            reading_hours = total_pages_read * 2  # Assume 2 minutes per page
            
            # Calculate reading streak
            reading_streak = 0
            today = datetime.now().date()
            recent_activity = ReadingProgress.objects.filter(
                user=user,
                updated_at__gte=today - timedelta(days=30)
            ).order_by('-updated_at')
            
            if recent_activity.exists():
                streak_days = set()
                for activity in recent_activity:
                    streak_days.add(activity.updated_at.date())
                
                streak_days = sorted(streak_days, reverse=True)
                current_streak = 0
                
                for i, date in enumerate(streak_days):
                    if i == 0:
                        current_streak = 1
                    elif streak_days[i-1] - date == timedelta(days=1):
                        current_streak += 1
                    else:
                        break
                
                reading_streak = current_streak
            
            # Calculate achievements
            achievements = 0
            if books_read >= 1:
                achievements += 1
            if books_read >= 5:
                achievements += 1
            if books_read >= 10:
                achievements += 1
            if reading_streak >= 7:
                achievements += 1
            if reading_streak >= 30:
                achievements += 1
            
            profile_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined,
                'is_staff': user.is_staff,
                'avatar': getattr(user, 'avatar', None),
                'bio': getattr(user, 'bio', ''),
                'favorite_genres': getattr(user, 'favorite_genres', ''),
                'reading_goal': getattr(user, 'reading_goal', 2),
                'books_read': books_read,
                'reading_hours': reading_hours,
                'reading_streak': reading_streak,
                'achievements': achievements,
            }
            
            logger.info(f"👤 Profile data for {user.username}: {profile_data}")
            return Response(profile_data)
        
        elif request.method == 'PUT':
            # Update user profile
            data = request.data
            
            # Update basic fields
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'email' in data:
                user.email = data['email']
            if 'username' in data:
                user.username = data['username']
            
            # Update custom profile fields (if they exist)
            if hasattr(user, 'bio') and 'bio' in data:
                user.bio = data['bio']
            if hasattr(user, 'avatar') and 'avatar' in data:
                user.avatar = data['avatar']
            if hasattr(user, 'favorite_genres') and 'favorite_genres' in data:
                user.favorite_genres = data['favorite_genres']
            if hasattr(user, 'reading_goal') and 'reading_goal' in data:
                user.reading_goal = int(data['reading_goal'])
            
            user.save()
            
            logger.info(f"✅ Profile updated for {user.username}")
            return Response({'message': 'Profile updated successfully'})
        
    except Exception as e:
        logger.error(f"Error in user profile: {e}")
        return Response(
            {'error': 'Failed to process profile request'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_reading_progress(request):
    """Update reading progress for a book"""
    try:
        user = request.user
        book_id = request.data.get('book_id')
        progress = request.data.get('progress', 0)
        current_page = request.data.get('current_page')
        
        if not book_id:
            return Response(
                {'error': 'Book ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user has access to the book
        library_entry = UserLibrary.objects.filter(
            user=user, 
            book_id=book_id, 
            is_active=True
        ).first()
        
        if not library_entry:
            return Response(
                {'error': 'Book not found in your library'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create reading progress
        reading_progress, created = ReadingProgress.objects.get_or_create(
            user=user,
            book_id=book_id,
            defaults={
                'current_page': current_page or 1,
                'total_pages': library_entry.book.pages or 0,
                'progress_percentage': progress
            }
        )
        
        if not created:
            reading_progress.current_page = current_page or reading_progress.current_page
            reading_progress.progress_percentage = progress
            reading_progress.save()
        
        logger.info(f"📖 Reading progress updated for {user.username}, book {book_id}: {progress}%")
        
        return Response({
            'message': 'Reading progress updated',
            'progress': reading_progress.progress_percentage,
            'current_page': reading_progress.current_page
        })
        
    except Exception as e:
        logger.error(f"Error updating reading progress: {e}")
        return Response(
            {'error': 'Failed to update reading progress'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
