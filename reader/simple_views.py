from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from books.models import Book
from library.models import UserLibrary, ReadingProgress
import json

class SimpleReaderViewSet(viewsets.GenericViewSet):
    """
    Simple ViewSet for basic reading functionality
    """
    permission_classes = [IsAuthenticated]
    
    def get_user_id(self):
        """Get user ID from JWT token"""
        return self.request.user_payload.get('user_id')
    
    def verify_book_access(self, book_id):
        """Verify user has access to the book"""
        user_id = self.get_user_id()
        try:
            book = Book.objects.get(id=book_id)
            if not UserLibrary.objects.filter(user_id=user_id, book=book, is_active=True).exists():
                return None, Response(
                    {'error': 'You do not have access to this book'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            return book, None
        except Book.DoesNotExist:
            return None, Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def read(self, request, pk=None):
        """Get book content for reading"""
        user_id = self.get_user_id()
        
        try:
            book = Book.objects.get(id=pk)
            
            # Verify user has access
            if not UserLibrary.objects.filter(user_id=user_id, book=book, is_active=True).exists():
                return Response(
                    {'error': 'You do not have access to this book'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get reading progress
            try:
                progress = ReadingProgress.objects.get(user_id=user_id, book=book)
                current_page = progress.current_page
            except ReadingProgress.DoesNotExist:
                current_page = 1
                # Create initial progress
                ReadingProgress.objects.create(
                    user_id=user_id,
                    book=book,
                    current_page=1,
                    total_pages=book.total_pages
                )
            
            # Get book content (simplified for demo)
            book_data = {
                'id': book.id,
                'title': book.title,
                'author': book.author.name if book.author else 'Unknown',
                'description': book.description,
                'total_pages': book.total_pages,
                'current_page': current_page,
                'content': f'''
                    <h2>{book.title}</h2>
                    <p><strong>Author:</strong> {book.author.name if book.author else 'Unknown'}</p>
                    <p><strong>Description:</strong> {book.description}</p>
                    <hr>
                    <div class="chapter">
                        <h3>Chapter {current_page}</h3>
                        <p>This is the content for page {current_page} of "{book.title}". 
                        In a real implementation, this would contain the actual book content 
                        extracted from the PDF file.</p>
                        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
                        Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
                        <p>Ut enim ad minim veniam, quis nostrud exercitation ullamco 
                        laboris nisi ut aliquip ex ea commodo consequat.</p>
                    </div>
                '''
            }
            
            return Response(book_data)
            
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to load book: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def update_progress(self, request):
        """Update reading progress"""
        user_id = self.get_user_id()
        book_id = request.data.get('book_id')
        current_page = request.data.get('current_page')
        total_pages = request.data.get('total_pages')
        
        try:
            book = Book.objects.get(id=book_id)
            
            # Verify user has access
            if not UserLibrary.objects.filter(user_id=user_id, book=book, is_active=True).exists():
                return Response(
                    {'error': 'You do not have access to this book'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Update or create progress
            progress, created = ReadingProgress.objects.update_or_create(
                user_id=user_id,
                book=book,
                defaults={
                    'current_page': current_page,
                    'total_pages': total_pages,
                    'last_read_at': timezone.now()
                }
            )
            
            if not created:
                progress.current_page = current_page
                progress.total_pages = total_pages
                progress.last_read_at = timezone.now()
                progress.save()
            
            return Response({
                'success': True,
                'current_page': current_page,
                'total_pages': total_pages
            })
            
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to update progress: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
