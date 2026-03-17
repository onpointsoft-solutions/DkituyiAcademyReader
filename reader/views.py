from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from books.models import Book
from library.models import UserLibrary, ReadingProgress, ReadingSession


class ReaderViewSet(viewsets.GenericViewSet):
    """
    ViewSet for book reading functionality
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def progress(self, request):
        """Update reading progress for a book"""
        user_id = request.user_payload.get('user_id')
        book_id = request.data.get('book_id')
        page = request.data.get('page', 1)
        total_pages = request.data.get('total_pages')
        
        if not book_id:
            return Response(
                {'error': 'book_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            book = Book.objects.get(id=book_id)
            
            # Check if user has access to this book
            if not UserLibrary.objects.filter(
                user_id=user_id, 
                book=book
            ).first():
                return Response(
                    {'error': 'Access denied to this book'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get or create reading progress
            progress, created = ReadingProgress.objects.get_or_create(
                user_id=user_id,
                book=book,
                defaults={
                    'current_page': page,
                    'total_pages': total_pages or book.pages
                }
            )
            
            # Update progress
            progress.update_progress(page, total_pages or book.pages)
            
            return Response({
                'message': 'Progress updated successfully',
                'progress': {
                    'current_page': progress.current_page,
                    'total_pages': progress.total_pages,
                    'progress_percentage': progress.progress_percentage,
                    'is_completed': progress.is_completed
                }
            })
            
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def start_session(self, request):
        """Start a reading session"""
        user_id = request.user_payload.get('user_id')
        book_id = request.data.get('book_id')
        start_page = request.data.get('start_page', 1)
        
        if not book_id:
            return Response(
                {'error': 'book_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            book = Book.objects.get(id=book_id)
            
            # Check if user has access to this book
            if not UserLibrary.objects.filter(
                user_id=user_id, 
                book=book
            ).first():
                return Response(
                    {'error': 'Access denied to this book'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
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
            }, status=status.HTTP_201_CREATED)
            
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def end_session(self, request):
        """End a reading session"""
        user_id = request.user_payload.get('user_id')
        session_id = request.data.get('session_id')
        end_page = request.data.get('end_page')
        
        if not session_id:
            return Response(
                {'error': 'session_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session = ReadingSession.objects.get(
                id=session_id, 
                user_id=user_id
            )
            
            session.end_session(end_page)
            
            return Response({
                'message': 'Reading session ended',
                'duration_minutes': session.duration_minutes
            })
            
        except ReadingSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def book_pdf(self, request):
        """Serve PDF file for a book (protected)"""
        user_id = request.user_payload.get('user_id')
        book_id = request.GET.get('book_id')
        
        if not book_id:
            return Response(
                {'error': 'book_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            book = Book.objects.get(id=book_id)
            
            # Check if user has access to this book
            if not UserLibrary.objects.filter(
                user_id=user_id, 
                book=book
            ).first():
                return Response(
                    {'error': 'Access denied to this book'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if not book.pdf_file:
                return Response(
                    {'error': 'PDF file not available'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Serve the PDF file
            response = HttpResponse(book.pdf_file.open('rb'), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{book.title}.pdf"'
            response['Content-Length'] = book.file_size
            return response
            
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
