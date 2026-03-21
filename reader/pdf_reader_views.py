from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from books.models import Book
from library.models import UserLibrary, ReadingProgress
import json
import os
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

class PDFReaderViewSet(viewsets.GenericViewSet):
    """
    ViewSet for PDF reading with PyPDF2 content extraction
    """
    permission_classes = []  # Allow access without authentication for PDF reader
    
    def get_user_id(self):
        """Get user ID from JWT token or session"""
        try:
            # Try to get from user_payload (JWT auth)
            return self.request.user_payload.get('user_id')
        except AttributeError:
            # Fallback to authenticated user
            if hasattr(self.request, 'user') and self.request.user.is_authenticated:
                return self.request.user.id
            # For demo purposes, return a default user ID
            return 3  # This should be replaced with proper authentication
    
    def verify_book_access(self, book_id):
        """Verify user has access to the book"""
        user_id = self.get_user_id()
        try:
            book = Book.objects.get(id=book_id)
            # For demo, allow access to all books
            # In production, uncomment the line below:
            # if not UserLibrary.objects.filter(user_id=user_id, book=book, is_active=True).exists():
            #     return None, Response(
            #         {'error': 'You do not have access to this book'}, 
            #         status=status.HTTP_403_FORBIDDEN
            #     )
            return book, None
        except Book.DoesNotExist:
            return None, Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def extract_pdf_text(self, pdf_file_path, page_number=None):
        """Extract text from PDF using PyPDF2"""
        try:
            if not os.path.exists(pdf_file_path):
                return None, "PDF file not found"
            
            with open(pdf_file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                if page_number is not None:
                    # Extract specific page
                    if page_number < 1 or page_number > total_pages:
                        return None, f"Page {page_number} not found (total pages: {total_pages})"
                    
                    page = pdf_reader.pages[page_number - 1]  # PyPDF2 is 0-indexed
                    text = page.extract_text()
                    return text, None
                else:
                    # Extract all pages
                    all_text = ""
                    for page_num, page in enumerate(pdf_reader.pages):
                        page_text = page.extract_text()
                        all_text += f"<div class='page' data-page='{page_num + 1}'>"
                        all_text += f"<h3>Page {page_num + 1}</h3>"
                        all_text += f"<div class='page-content'>{page_text}</div>"
                        all_text += "</div>"
                    return all_text, None
                    
        except PdfReadError as e:
            return None, f"PDF read error: {str(e)}"
        except Exception as e:
            return None, f"Error extracting PDF text: {str(e)}"
    
    @action(detail=True, methods=['get'])
    def read_pdf(self, request, pk=None):
        """Get PDF content for reading using PyPDF2"""
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
            
            # Extract PDF content
            if book.pdf_file:
                pdf_file_path = book.pdf_file.path
                text_content, error = self.extract_pdf_text(pdf_file_path)
                
                if error:
                    return Response(
                        {'error': f'Failed to extract PDF content: {error}'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                book_data = {
                    'id': book.id,
                    'title': book.title,
                    'author': book.author.name if book.author else 'Unknown',
                    'description': book.description,
                    'total_pages': book.total_pages,
                    'current_page': current_page,
                    'content': text_content,
                    'pdf_file_url': book.pdf_file.url if book.pdf_file else None
                }
            else:
                # Fallback to book description if no PDF
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
                            <h3>Book Content</h3>
                            <p>No PDF file available for this book. Showing book description only.</p>
                        </div>
                    ''',
                    'pdf_file_url': None
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
    
    @action(detail=True, methods=['get'])
    def read_page(self, request, pk=None):
        """Get specific page content from PDF"""
        user_id = self.get_user_id()
        page_number = request.GET.get('page', 1)
        
        try:
            page_number = int(page_number)
        except (ValueError, TypeError):
            page_number = 1
        
        try:
            book = Book.objects.get(id=pk)
            
            # Verify user has access
            if not UserLibrary.objects.filter(user_id=user_id, book=book, is_active=True).exists():
                return Response(
                    {'error': 'You do not have access to this book'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Extract PDF page content
            if book.pdf_file:
                pdf_file_path = book.pdf_file.path
                text_content, error = self.extract_pdf_text(pdf_file_path, page_number)
                
                if error:
                    return Response(
                        {'error': f'Failed to extract PDF page: {error}'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                page_data = {
                    'page_number': page_number,
                    'content': text_content,
                    'total_pages': book.total_pages
                }
            else:
                page_data = {
                    'page_number': page_number,
                    'content': f'Page {page_number} content not available (no PDF file)',
                    'total_pages': book.total_pages
                }
            
            return Response(page_data)
            
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to load page: {str(e)}'}, 
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
