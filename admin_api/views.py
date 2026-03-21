from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from books.models import Book, Author
from library.models import UserLibrary, ReadingProgress, ReadingSession
from .permissions import IsStaffUser
from .serializers import AdminBookWriteSerializer, AdminBookListSerializer
from core.email import EmailService


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
        
        book = serializer.save()
        
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
