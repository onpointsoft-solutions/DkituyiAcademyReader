from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.db import connection
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from books.models import Book, Author
from library.models import UserLibrary, ReadingProgress, ReadingSession
from .permissions import IsStaffUser
from .serializers import AdminBookWriteSerializer, AdminBookListSerializer
from core.email import EmailService


class AdminSystemHealthView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        try:
            # Database health check
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_status = "healthy" if cursor.fetchone() else "error"
        except Exception:
            db_status = "error"

        # API server status (always healthy if we can respond)
        api_status = "healthy"

        # Calculate uptime (simplified - using Django start time)
        import time
        uptime_seconds = time.time() - time.time()  # Fallback
        uptime_days = int(uptime_seconds // (24 * 3600))

        # Memory usage (simplified - skip psutil dependency)
        memory_usage = "N/A"

        return Response({
            'database_status': db_status,
            'api_status': api_status,
            'uptime_days': uptime_days,
            'memory_usage': memory_usage,
        })


class AdminRecentActivityView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        # Recent reading activity (last 20 sessions)
        recent_sessions = (
            ReadingSession.objects.select_related('book')
            .order_by('-start_time')[:20]
        )
        recent_activity = []
        
        for s in recent_sessions:
            try:
                # Get user info separately to avoid select_related issues
                user = User.objects.filter(id=s.user_id).first()
                username = user.username if user else 'Unknown User'
                
                recent_activity.append({
                    'id': s.id,
                    'type': 'book_read',
                    'description': f'{username} started reading "{s.book.title}"',
                    'timestamp': s.start_time.isoformat(),
                    'user_id': s.user_id,
                    'book_id': s.book_id,
                })
            except Exception as e:
                # Handle cases where user might not exist or other errors
                recent_activity.append({
                    'id': s.id,
                    'type': 'book_read',
                    'description': f'Someone started reading "{s.book.title}"',
                    'timestamp': s.start_time.isoformat(),
                    'user_id': s.user_id,
                    'book_id': s.book_id,
                })

        # Add some user registration activity
        recent_users = User.objects.order_by('-date_joined')[:10]
        for user in recent_users:
            recent_activity.append({
                'id': f'user_{user.id}',
                'type': 'user_register',
                'description': f'New user "{user.username}" registered',
                'timestamp': user.date_joined.isoformat(),
                'user_id': user.id,
            })

        # Sort by timestamp
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return Response(recent_activity[:20])


class AdminUserProgressView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        """Get user progress information for testing"""
        from library.models import UserLibrary, ReadingProgress
        from reader.models import UnlockedPage
        
        # Get admin user for testing
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user = User.objects.filter(username='vincentAdmin').first()
        
        if not admin_user:
            return Response({'error': 'Admin user not found'}, status=404)
        
        # Get library entries
        library_entries = UserLibrary.objects.filter(user_id=admin_user.id).select_related('book')
        
        progress_data = []
        for entry in library_entries:
            book = entry.book
            reading_progress = ReadingProgress.objects.filter(
                user_id=admin_user.id, 
                book=book
            ).first()
            
            unlocked_pages = list(UnlockedPage.objects.filter(
                user_id=admin_user.id,
                book=book
            ).values_list('page_number', flat=True))
            
            progress_data.append({
                'book_id': book.id,
                'book_title': book.title,
                'book_author': book.author.name,
                'in_library': True,
                'purchased': entry.purchased,
                'current_page': reading_progress.current_page if reading_progress else 1,
                'total_pages': reading_progress.total_pages if reading_progress else book.pages,
                'progress_percentage': reading_progress.progress_percentage if reading_progress else 0.0,
                'unlocked_pages_count': len(unlocked_pages),
                'unlocked_pages': unlocked_pages[:10],  # Show first 10 for brevity
                'last_read': reading_progress.last_read if reading_progress else None,
                'is_completed': reading_progress.is_completed if reading_progress else False,
            })
        
        return Response({
            'user_id': admin_user.id,
            'username': admin_user.username,
            'total_books_in_library': len(library_entries),
            'progress_data': progress_data
        })


class AdminBookListView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        books = Book.objects.all().order_by('-created_at')
        book_list = []
        for book in books:
            book_list.append({
                'id': book.id,
                'title': book.title,
                'author': book.author.name,
                'has_pdf': bool(book.pdf_file),
                'pdf_file_name': book.pdf_file.name if book.pdf_file else None,
                'content_source': book.content_source,
                'is_free': book.is_free,
                'created_at': book.created_at.isoformat() if book.created_at else None,
            })
        return Response({'results': book_list})


class AdminStatsView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        from django.db.models import Count
        total_books = Book.objects.count()
        total_users = User.objects.count()
        total_reads = ReadingSession.objects.count()
        total_library_entries = UserLibrary.objects.count()
        completed_reads = ReadingProgress.objects.filter(is_completed=True).count()

        # Optional: sessions in last 30 days for "growth"
        since = timezone.now() - timezone.timedelta(days=30)
        recent_sessions = ReadingSession.objects.filter(start_time__gte=since).count()
        prev_since = since - timezone.timedelta(days=30)
        prev_sessions = ReadingSession.objects.filter(
            start_time__gte=prev_since, start_time__lt=since
        ).count()
        monthly_growth = None
        if prev_sessions:
            monthly_growth = round(((recent_sessions - prev_sessions) / prev_sessions) * 100, 1)
        elif recent_sessions:
            monthly_growth = 100.0

        avg_rating_obj = Book.objects.aggregate(avg_rating=Avg('rating'))
        avg_rating = round(float(avg_rating_obj['avg_rating'] or 0), 1)

        return Response({
            'totalBooks': total_books,
            'totalUsers': total_users,
            'totalReads': total_reads,
            'totalLibraryEntries': total_library_entries,
            'completedReads': completed_reads,
            'monthlyGrowth': monthly_growth,
            'avgRating': avg_rating,
            'revenue': 0,  # placeholder
        })


class AdminUserListView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        users = User.objects.all().order_by('-date_joined')[:200]
        user_list = []
        for u in users:
            lib_count = UserLibrary.objects.filter(user_id=u.id).count()
            progress_count = ReadingProgress.objects.filter(user_id=u.id).count()
            user_list.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'is_staff': u.is_staff,
                'is_superuser': u.is_superuser,
                'date_joined': u.date_joined.isoformat() if u.date_joined else None,
                'library_count': lib_count,
                'reading_progress_count': progress_count,
            })
        return Response({'results': user_list})


class AdminReportsView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        # Top books by reading progress count (most users reading or completed)
        top_books = (
            ReadingProgress.objects.values('book')
            .annotate(read_count=Count('id'), completed=Count('id', filter=Q(is_completed=True)))
            .order_by('-read_count')[:10]
        )
        book_ids = [b['book'] for b in top_books]
        books_qs = Book.objects.filter(id__in=book_ids).in_bulk()
        top_books_data = []
        for b in top_books:
            book = books_qs.get(b['book'])
            if book:
                top_books_data.append({
                    'id': book.id,
                    'title': book.title,
                    'author_name': book.author.name,
                    'read_count': b['read_count'],
                    'completed_count': b['completed'],
                })

        # Recent reading activity (last 50 sessions)
        recent_sessions = (
            ReadingSession.objects.select_related('book')
            .order_by('-start_time')[:50]
        )
        recent_activity = [
            {
                'id': s.id,
                'user_id': s.user_id,
                'book_title': s.book.title,
                'book_id': s.book_id,
                'start_time': s.start_time.isoformat(),
                'duration_minutes': s.duration_minutes,
            }
            for s in recent_sessions
        ]

        # Summary stats for charts
        last_7_days = []
        for i in range(6, -1, -1):
            day = timezone.now().date() - timezone.timedelta(days=i)
            count = ReadingSession.objects.filter(start_time__date=day).count()
            last_7_days.append({'date': day.isoformat(), 'sessions': count})

        return Response({
            'topBooks': top_books_data,
            'recentActivity': recent_activity,
            'sessionsByDay': last_7_days,
        })


class AdminBookViewSet(viewsets.ModelViewSet):
    # Temporarily remove permission class to test
    # permission_classes = [IsStaffUser]
    queryset = Book.objects.all().order_by('-created_at')

    def dispatch(self, request, *args, **kwargs):
        print(f"DEBUG: AdminBookViewSet.dispatch called")
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: Request path: {request.path}")
        print(f"DEBUG: user_payload: {getattr(request, 'user_payload', None)}")
        
        # Manual permission check for testing
        if hasattr(request, 'user_payload') and request.user_payload:
            user_id = request.user_payload.get('user_id')
            print(f"DEBUG: Checking user_id: {user_id}")
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(id=user_id)
                print(f"DEBUG: Manual check - User: {user.username}, is_staff: {user.is_staff}")
                if not (user.is_staff or user.is_superuser):
                    print(f"DEBUG: Permission denied - user is not staff")
                    return Response({'error': 'Staff access required'}, status=403)
                print(f"DEBUG: Permission check passed - proceeding with super().dispatch()")
            except User.DoesNotExist:
                print(f"DEBUG: User.DoesNotExist for user_id: {user_id}")
                return Response({'error': 'User not found'}, status=403)
        else:
            print(f"DEBUG: No user_payload found - permission denied")
            return Response({'error': 'Authentication required'}, status=401)
        
        try:
            response = super().dispatch(request, *args, **kwargs)
            print(f"DEBUG: super().dispatch() completed successfully")
            return response
        except Exception as e:
            print(f"DEBUG: Exception in super().dispatch(): {e}")
            print(f"DEBUG: Exception type: {type(e)}")
            raise

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AdminBookWriteSerializer
        return AdminBookListSerializer

    def create(self, request, *args, **kwargs):
        print(f"DEBUG: AdminBookViewSet.create called")
        print(f"DEBUG: user_payload: {getattr(request, 'user_payload', None)}")
        if hasattr(request, 'user_payload') and request.user_payload:
            print(f"DEBUG: Getting user_id: {request.user_payload.get('user_id')}")
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        # Handle file size calculation
        if serializer.validated_data.get('pdf_file'):
            file_size = serializer.validated_data['pdf_file'].size
            serializer.validated_data['file_size'] = file_size
            print(f"🔍 DEBUG: PDF file processed: {serializer.validated_data['pdf_file'].name} ({file_size} bytes)")
        
        # Handle cover image
        if serializer.validated_data.get('cover_image'):
            cover_size = serializer.validated_data['cover_image'].size
            print(f"🔍 DEBUG: Cover image processed: {serializer.validated_data['cover_image'].name} ({cover_size} bytes)")
        
        book = serializer.save()
        print(f"🔍 DEBUG: Book created successfully: {book.title} (ID: {book.id})")
        if book.cover_image:
            print(f"🔍 DEBUG: Cover image saved at: {book.cover_image.url}")
        if book.cover_url:
            print(f"🔍 DEBUG: Cover URL: {book.cover_url}")
        
        # Send email notifications to all users about new book
        try:
            users = User.objects.all()
            for user in users:
                EmailService.send_book_notification(
                    user_email=user.email,
                    book_title=book.title,
                    author_name=book.author.name if book.author else "African Author",
                    book_description=book.description[:200] + "..." if book.description and len(book.description) > 200 else (book.description or "A new African book has been added to our collection!")
                )
            
            # Send admin notification
            EmailService.send_admin_notification(
                subject="New Book Added",
                message=f"Book '{book.title}' by {book.author.name if book.author else 'Unknown Author'} has been added to the dkituyi academy library."
            )
        except Exception as e:
            # Log error but don't fail the book creation
            print(f"Failed to send book notification emails: {e}")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        # Handle file size calculation for new uploads
        if serializer.validated_data.get('pdf_file'):
            file_size = serializer.validated_data['pdf_file'].size
            serializer.validated_data['file_size'] = file_size
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Delete associated files
        if instance.pdf_file:
            try:
                instance.pdf_file.delete(save=False)
            except Exception as e:
                # Log error but don't fail the deletion
                print(f"Error deleting PDF file: {e}")
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
