from django.db import models
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import UserLibrary, ReadingProgress, ReadingSession
from .serializers import UserLibrarySerializer, ReadingProgressSerializer, ReadingSessionSerializer
from books.models import Book


class LibraryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing user's library
    """
    serializer_class = UserLibrarySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    
    def get_queryset(self):
        user_id = self.request.user_payload.get('user_id') if self.request.user_payload else None
        if user_id:
            return UserLibrary.objects.filter(user_id=user_id)
        return UserLibrary.objects.none()
    
    def list(self, request):
        """Get user's library with books from WooCommerce"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # First, sync library with WooCommerce
        self._sync_with_woocommerce(user_id)
        
        # Get user's library
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def _sync_with_woocommerce(self, user_id):
        """Sync user's purchased books with WooCommerce"""
        try:
            # Get orders from WooCommerce API
            headers = {}
            if settings.WOOCOMMERCE_CONSUMER_KEY and settings.WOOCOMMERCE_CONSUMER_SECRET:
                auth = (settings.WOOCOMMERCE_CONSUMER_KEY, settings.WOOCOMMERCE_CONSUMER_SECRET)
            else:
                return  # Skip sync if credentials not configured
            
            # Get customer orders
            response = requests.get(
                f"{settings.WOOCOMMERCE_API_URL}/orders",
                params={'customer': user_id, 'status': 'completed'},
                headers=headers,
                auth=auth,
                timeout=10
            )
            
            if response.status_code == 200:
                orders = response.json()
                for order in orders:
                    for item in order.get('line_items', []):
                        # Try to find book by SKU or title
                        book = None
                        if item.get('sku'):
                            book = Book.objects.filter(isbn=item['sku']).first()
                        
                        if not book:
                            book = Book.objects.filter(title__icontains=item['name']).first()
                        
                        if book:
                            # Add to user library
                            UserLibrary.objects.get_or_create(
                                user_id=user_id,
                                book=book,
                                defaults={
                                    'purchase_date': timezone.now(),
                                    'is_active': True
                                }
                            )
        
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error syncing with WooCommerce: {e}")
    
    @action(detail=False, methods=['get'])
    def reading_progress(self, request):
        """Get user's reading progress for all books"""
        user_id = request.user_payload.get('user_id')
        progress = ReadingProgress.objects.filter(user_id=user_id)
        serializer = ReadingProgressSerializer(progress, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get user's reading session history"""
        user_id = request.user_payload.get('user_id')
        sessions = ReadingSession.objects.filter(user_id=user_id)
        serializer = ReadingSessionSerializer(sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_book(self, request):
        """Manually add a book to user's library (for testing)"""
        user_id = request.user_payload.get('user_id')
        book_id = request.data.get('book_id')
        
        if not book_id:
            return Response(
                {'error': 'book_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            book = Book.objects.get(id=book_id)
            library_entry, created = UserLibrary.objects.get_or_create(
                user_id=user_id,
                book=book,
                defaults={
                    'purchase_date': timezone.now(),
                    'is_active': True
                }
            )
            
            if created:
                return Response(
                    {'message': 'Book added to library successfully'},
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {'message': 'Book already in library'},
                    status=status.HTTP_200_OK
                )
        
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class UserLibraryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user library management with Django users
    """
    serializer_class = UserLibrarySerializer
    permission_classes = []  # Remove IsAuthenticated to use custom auth
    
    def get_queryset(self):
        user_id = self.request.user_payload.get('user_id') if self.request.user_payload else None
        if user_id:
            return UserLibrary.objects.filter(user_id=user_id)
        return UserLibrary.objects.none()
    
    def list(self, request):
        """Get user's library with automatic book assignment for new users"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        print(f"DEBUG: Getting library for user_id: {user_id}")
        
        # Check if user has any books in library
        library_count = UserLibrary.objects.filter(user_id=user_id).count()
        print(f"DEBUG: User library count: {library_count}")
        
        # If user has no books, add some sample books
        if library_count == 0:
            print(f"DEBUG: Adding sample books to user library")
            try:
                # Get some sample books
                sample_books = Book.objects.all()[:5]  # Get first 5 books
                for book in sample_books:
                    library_entry, created = UserLibrary.objects.get_or_create(
                        user_id=user_id,
                        book=book,
                        defaults={
                            'purchase_date': timezone.now(),
                            'is_active': True
                        }
                    )
                    
                    # Also create initial reading progress for variety
                    if created:
                        # Calculate realistic progress based on book properties
                        # Don't use random - use deterministic logic based on book ID
                        
                        # Use book ID to create consistent progress
                        book_id_hash = book.id % 100
                        initial_progress = 0
                        
                        # Deterministic progress calculation based on book properties
                        if book_id_hash < 20:  # 20% of books have no progress
                            initial_progress = 0
                            reading_time = 0
                        elif book_id_hash < 40:  # 20% have just started
                            initial_progress = 5
                            reading_time = 30
                        elif book_id_hash < 60:  # 20% have moderate progress
                            initial_progress = 25
                            reading_time = 90
                        elif book_id_hash < 80:  # 20% have good progress
                            initial_progress = 60
                            reading_time = 150
                        else:  # 20% are nearly finished
                            initial_progress = 85
                            reading_time = 200
                        
                        # Calculate current page based on progress
                        current_page = max(1, int((initial_progress / 100) * book.pages)) if book.pages > 0 else 1
                        
                        # Set last read date based on progress (more recent = more progress)
                        days_ago = 7 - (initial_progress // 15)  # Higher progress = more recent
                        last_read = timezone.now() - timedelta(days=days_ago) if initial_progress > 0 else None
                        
                        # Create reading progress
                        progress_entry = ReadingProgress.objects.get_or_create(
                            user_id=user_id,
                            book=book,
                            defaults={
                                'current_page': current_page,
                                'total_pages': book.pages,
                                'progress_percentage': initial_progress,
                                'is_completed': initial_progress >= 100,
                                'reading_time_minutes': reading_time,
                                'last_read': last_read
                            }
                        )[0]
                        
                        # Create reading session if there's reading time
                        if reading_time > 0 and last_read:
                            ReadingSession.objects.get_or_create(
                                user_id=user_id,
                                book=book,
                                defaults={
                                    'start_page': max(1, current_page - 10),
                                    'end_page': current_page,
                                    'duration_minutes': reading_time,
                                    'start_time': last_read - timedelta(minutes=reading_time),
                                    'end_time': last_read
                                }
                            )
                            print(f"DEBUG: Created reading session for book '{book.title}' with {reading_time}min ({initial_progress}% progress)")
                    
                    print(f"DEBUG: Added book '{book.title}' to user library")
            except Exception as e:
                print(f"DEBUG: Error adding sample books: {e}")
            
            # Refresh the library count after adding books
            library_count = UserLibrary.objects.filter(user_id=user_id).count()
            print(f"DEBUG: Updated user library count: {library_count}")
        
        # Get user's library
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Add a book to user's library"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        book_id = request.data.get('book_id')
        if not book_id:
            return Response(
                {'error': 'book_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            book = Book.objects.get(id=book_id)
            print(f"DEBUG: Adding book '{book.title}' to user {user_id} library")
            
            library_entry, created = UserLibrary.objects.get_or_create(
                user_id=user_id,
                book=book,
                defaults={
                    'purchase_date': timezone.now(),
                    'is_active': True
                }
            )
            
            if created:
                print(f"🔍 DEBUG: ✅ Book '{book.title}' successfully added to library!")
                return Response(
                    {
                        'message': f'📚 "{book.title}" has been added to your library!',
                        'book_title': book.title,
                        'book_id': book.id,
                        'author': book.author.name if book.author else 'Unknown',
                        'success': True
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                print(f"🔍 DEBUG: 📖 Book '{book.title}' already in library")
                return Response(
                    {
                        'message': f'📖 "{book.title}" is already in your library!',
                        'book_title': book.title,
                        'book_id': book.id,
                        'author': book.author.name if book.author else 'Unknown',
                        'already_exists': True
                    },
                    status=status.HTTP_200_OK
                )
        
        except Book.DoesNotExist:
            print(f"🔍 DEBUG: ❌ Book with ID {book_id} not found")
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def destroy(self, request, pk=None):
        """Remove a book from user's library"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            library_entry = UserLibrary.objects.get(user_id=user_id, book_id=pk)
            library_entry.delete()
            return Response(
                {'message': 'Book removed from library successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except UserLibrary.DoesNotExist:
            return Response(
                {'error': 'Book not found in library'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class UserStatsViewSet(viewsets.ViewSet):
    """
    ViewSet for user reading statistics
    """
    permission_classes = []  # Remove IsAuthenticated to use custom auth
    
    def list(self, request):
        """Get user's reading statistics"""
        print(f"🔍 DEBUG: UserStatsViewSet.list called")
        print(f"🔍 DEBUG: user_payload: {getattr(request, 'user_payload', 'None')}")
        
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            print(f"🔍 DEBUG: No user_id found in request")
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        print(f"🔍 DEBUG: Getting stats for user_id: {user_id}")
        
        # Get real user statistics
        try:
            # Get user's library count
            total_books = UserLibrary.objects.filter(user_id=user_id, is_active=True).count()
            
            # Get reading progress statistics
            progress_entries = ReadingProgress.objects.filter(user_id=user_id)
            books_read = progress_entries.filter(is_completed=True).count()
            in_progress = progress_entries.filter(is_completed=False).count()
            
            # Calculate total reading time
            total_reading_time = progress_entries.aggregate(
                total_time=Sum('reading_time_minutes')
            )['total_time'] or 0
            
            # Get reading streak (consecutive days with reading activity)
            # If no reading sessions exist, create them from reading progress data
            if not ReadingSession.objects.filter(user_id=user_id).exists():
                print(f"🔍 DEBUG: No reading sessions found, creating from progress data")
                for progress in progress_entries:
                    if progress.reading_time_minutes > 0 and progress.last_read:
                        # Create a reading session based on the progress data
                        ReadingSession.objects.get_or_create(
                            user_id=user_id,
                            book=progress.book,
                            defaults={
                                'start_page': max(1, progress.current_page - 10),
                                'end_page': progress.current_page,
                                'duration_minutes': progress.reading_time_minutes,
                                'start_time': progress.last_read - timezone.timedelta(minutes=progress.reading_time_minutes),
                                'end_time': progress.last_read
                            }
                        )
                        print(f"🔍 DEBUG: Created reading session for book {progress.book.title}")
            
            # Get last 30 days of reading sessions
            since = timezone.now() - timedelta(days=30)
            recent_days = ReadingSession.objects.filter(
                user_id=user_id,
                start_time__gte=since
            ).values('start_time__date').annotate(
                session_count=Count('id')
            ).order_by('start_time__date')
            
            # Calculate reading streak (consecutive days with sessions)
            reading_streak = 0
            if recent_days.exists():
                reading_streak = 1
                for i in range(1, len(recent_days)):
                    current_date = recent_days[i]['start_time__date']
                    prev_date = recent_days[i-1]['start_time__date']
                    if (current_date - prev_date).days == 1:
                        reading_streak += 1
                    else:
                        break
            
            # Get achievements based on reading activity (enhanced criteria)
            achievements = 0
            if books_read >= 1:
                achievements += 1  # First book completed
            if total_reading_time >= 60:  # 1 hour
                achievements += 1  # Getting started
            if total_reading_time >= 300:  # 5 hours
                achievements += 1  # Dedicated reader
            if reading_streak >= 3:
                achievements += 1  # Consistent reader
            if in_progress >= 3:
                achievements += 1  # Multi-book reader
            if total_books >= 5:
                achievements += 1  # Book collector
            
            stats = {
                'totalBooks': total_books,
                'booksRead': books_read,
                'inProgress': in_progress,
                'readingTimeHours': round(total_reading_time / 60, 1),
                'readingStreak': reading_streak,
                'achievements': achievements,
                'totalReadingTimeMinutes': total_reading_time
            }
            
            print(f"🔍 DEBUG: User stats calculated: {stats}")
            return Response(stats)
            
        except Exception as e:
            print(f"🔍 DEBUG: Error calculating stats: {str(e)}")
            # Return default stats if calculation fails
            return Response({
                'totalBooks': 0,
                'booksRead': 0,
                'inProgress': 0,
                'readingTimeHours': 0,
                'readingStreak': 0,
                'achievements': 0,
                'totalReadingTimeMinutes': 0
            })


class UserRecentBooksViewSet(viewsets.ViewSet):
    """
    ViewSet for user's recent books
    """
    permission_classes = []  # Remove IsAuthenticated to use custom auth
    
    def list(self, request):
        """Get user's recent books with reading progress"""
        print(f"🔍 DEBUG: UserRecentBooksViewSet.list called")
        print(f"🔍 DEBUG: user_payload: {getattr(request, 'user_payload', 'None')}")
        
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            print(f"🔍 DEBUG: No user_id found in request")
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        print(f"🔍 DEBUG: Getting recent books for user_id: {user_id}")
        
        # Get user's library with reading progress
        library_entries = UserLibrary.objects.filter(user_id=user_id, is_active=True)
        
        recent_books = []
        for entry in library_entries:
            # Get reading progress for this book
            progress = ReadingProgress.objects.filter(user_id=user_id, book=entry.book).first()
            
            # Calculate reading progress percentage
            progress_percentage = 0
            if progress and entry.book.pages > 0:
                progress_percentage = (progress.current_page / entry.book.pages) * 100
            elif progress:
                progress_percentage = progress.progress_percentage
            
            # Ensure progress is capped at 100%
            progress_percentage = min(100, max(0, progress_percentage))
            
            # Calculate reading time for this book
            reading_time = progress.reading_time_minutes if progress else 0
            
            book_data = {
                'id': entry.book.id,
                'title': entry.book.title,
                'author_name': entry.book.author.name if entry.book.author else 'Unknown',
                'cover_url': entry.book.cover_url,
                'reading_progress': round(progress_percentage, 1),
                'last_read': progress.last_read if progress else None,
                'is_completed': progress.is_completed if progress else False,
                'current_page': progress.current_page if progress else 1,
                'total_pages': entry.book.pages,
                'rating': float(entry.book.rating) if entry.book.rating else 0,
                'reading_time_minutes': reading_time,
                'reading_time_hours': round(reading_time / 60, 1) if reading_time > 0 else 0
            }
            recent_books.append(book_data)
        
        # Sort by last read (most recent first), then by reading progress
        recent_books.sort(key=lambda x: (
            x['last_read'] or timezone.datetime.min.replace(tzinfo=timezone.UTC),
            -x['reading_progress']  # Higher progress first if same date
        ), reverse=True)
        
        print(f"🔍 DEBUG: Returning {len(recent_books)} recent books")
        return Response({'results': recent_books[:10]})  # Return top 10 recent books


class UserReadingProgressViewSet(viewsets.ViewSet):
    """
    ViewSet for managing user reading progress
    """
    permission_classes = []  # Remove IsAuthenticated to use custom auth
    
    def list(self, request):
        """Get user's reading progress for all books"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        progress_entries = ReadingProgress.objects.filter(user_id=user_id)
        progress_data = []
        
        for progress in progress_entries:
            progress_data.append({
                'book_id': progress.book.id,
                'book_title': progress.book.title,
                'current_page': progress.current_page,
                'total_pages': progress.total_pages,
                'progress_percentage': progress.progress_percentage,
                'is_completed': progress.is_completed,
                'reading_time_minutes': progress.reading_time_minutes,
                'last_read': progress.last_read
            })
        
        return Response({'results': progress_data})
    
    def create(self, request):
        """Update or create reading progress for a book"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        book_id = request.data.get('book_id')
        progress = request.data.get('progress', 0)
        current_page = request.data.get('current_page', 1)
        total_pages = request.data.get('total_pages', 0)
        
        if not book_id:
            return Response(
                {'error': 'book_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate progress range
        if progress < 0 or progress > 100:
            return Response(
                {'error': 'Progress must be between 0 and 100'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            book = Book.objects.get(id=book_id)
            
            # Get or create reading progress
            progress_entry, created = ReadingProgress.objects.get_or_create(
                user_id=user_id,
                book=book,
                defaults={
                    'current_page': current_page,
                    'total_pages': total_pages,
                    'progress_percentage': progress,
                    'is_completed': progress >= 100,
                    'reading_time_minutes': 0
                }
            )
            
            if not created:
                # Update existing progress
                progress_entry.current_page = current_page
                progress_entry.total_pages = total_pages
                progress_entry.progress_percentage = progress
                progress_entry.is_completed = progress >= 100
                progress_entry.last_read = timezone.now()
                progress_entry.save()
            
            # If book is completed, add to user library if not already there
            if progress >= 100:
                UserLibrary.objects.get_or_create(
                    user_id=user_id,
                    book=book,
                    defaults={'is_active': True}
                )
            
            print(f"🔍 DEBUG: Updated reading progress for user {user_id}, book {book.title}: {progress}%")
            
            return Response({
                'message': 'Reading progress updated successfully',
                'progress': progress,
                'is_completed': progress >= 100
            })
        
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"🔍 DEBUG: Error updating reading progress: {str(e)}")
            return Response(
                {'error': 'Failed to update reading progress'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def start_reading_session(self, request):
        """Start a new reading session"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        book_id = request.data.get('book_id')
        start_page = request.data.get('start_page', 1)
        
        try:
            book = Book.objects.get(id=book_id)
            
            # Create reading session
            session = ReadingSession.objects.create(
                user_id=user_id,
                book=book,
                start_page=start_page,
                start_time=timezone.now()
            )
            
            return Response({
                'session_id': session.id,
                'message': 'Reading session started'
            })
            
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def end_reading_session(self, request):
        """End a reading session and update progress"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        session_id = request.data.get('session_id')
        end_page = request.data.get('end_page')
        
        try:
            session = ReadingSession.objects.get(id=session_id, user_id=user_id)
            session.end_session(end_page)
            
            # Update reading progress
            progress_entry, created = ReadingProgress.objects.get_or_create(
                user_id=user_id,
                book=session.book,
                defaults={
                    'current_page': end_page,
                    'progress_percentage': (end_page / session.book.pages) * 100 if session.book.pages > 0 else 0,
                    'is_completed': False
                }
            )
            
            if not created:
                progress_entry.current_page = end_page
                progress_entry.progress_percentage = (end_page / session.book.pages) * 100 if session.book.pages > 0 else 0
                progress_entry.is_completed = progress_entry.progress_percentage >= 100
                progress_entry.reading_time_minutes += session.duration_minutes
                progress_entry.last_read = timezone.now()
                progress_entry.save()
            
            return Response({
                'message': 'Reading session ended',
                'progress': progress_entry.progress_percentage,
                'reading_time': progress_entry.reading_time_minutes
            })
            
        except ReadingSession.DoesNotExist:
            return Response(
                {'error': 'Reading session not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
