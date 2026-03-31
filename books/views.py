from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils.encoding import smart_str
import os
import logging

from .models import Book, BookReview
from .serializers import BookSerializer, BookListSerializer, BookReviewSerializer, PublicBookSerializer
from library.models import UserLibrary
from admin_api.permissions import IsStaffUser

logger = logging.getLogger(__name__)


class IsJWTAuthenticated(BasePermission):
    """
    Custom permission class that works with JWT middleware
    """
    def has_permission(self, request, view):
        print(f"DEBUG: IsJWTAuthenticated.has_permission called for {request.path}")
        print(f"DEBUG: hasattr(request, 'user_payload'): {hasattr(request, 'user_payload')}")
        print(f"DEBUG: request.user_payload: {getattr(request, 'user_payload', None)}")
        
        # Check if JWT middleware has set user_payload
        if hasattr(request, 'user_payload') and request.user_payload:
            print(f"DEBUG: JWT authentication passed")
            return True
        
        # Fallback to standard Django authentication
        has_user = hasattr(request, 'user')
        is_auth = has_user and hasattr(request.user, 'is_authenticated') and request.user.is_authenticated
        print(f"DEBUG: Django authentication - has_user: {has_user}, is_auth: {is_auth}")
        
        return is_auth


class BookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and creating books (admin can create, others can read)
    """
    queryset = Book.objects.all()
    # Remove class-level permission_classes to let get_permissions handle everything
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categories', 'author', 'language']
    search_fields = ['title', 'subtitle', 'description', 'author__name']
    ordering_fields = ['title', 'created_at', 'price', 'rating', 'publication_date']
    ordering = ['-created_at']
    
    def dispatch(self, request, *args, **kwargs):
        """
        Override dispatch to handle JWT authentication before permission checks
        """
        print(f"DEBUG: BookViewSet.dispatch called for {request.method} {request.path}")
        print(f"DEBUG: hasattr(request, 'user_payload'): {hasattr(request, 'user_payload')}")
        
        # Check if user is authenticated via JWT
        if hasattr(request, 'user_payload') and request.user_payload:
            print(f"DEBUG: User is authenticated via JWT, proceeding with request")
            return super().dispatch(request, *args, **kwargs)
        
        # If not authenticated, check if this is a read-only action
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            print(f"DEBUG: Allowing read-only request without authentication")
            return super().dispatch(request, *args, **kwargs)
        
        # For write operations, require authentication
        print(f"DEBUG: Authentication required for {request.method} request")
        from rest_framework.exceptions import AuthenticationFailed
        raise AuthenticationFailed("Authentication required")
    
    def get_permissions(self):
        """
        Admin users can create books, all authenticated users can read
        """
        print(f"DEBUG: BookViewSet.get_permissions called for action: {self.action}")
        
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsStaffUser]
            print(f"DEBUG: Using IsStaffUser permission for admin action: {self.action}")
        else:
            # Use a custom permission that works with JWT
            permission_classes = [IsJWTAuthenticated]
            print(f"DEBUG: Using IsJWTAuthenticated permission for read action: {self.action}")
        
        permissions = [permission() for permission in permission_classes]
        print(f"DEBUG: Permission classes: {[p.__class__.__name__ for p in permissions]}")
        return permissions

    def get_serializer_class(self):
        if self.action == 'list':
            return BookListSerializer
        return BookSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def create(self, request, *args, **kwargs):
        """Create a new book instance."""
        print(f"DEBUG: BookViewSet.create called")
        print(f"DEBUG: Request data: {request.data}")
        print(f"DEBUG: Request files: {request.FILES}")
        
        serializer = self.get_serializer(data=request.data)
        print(f"DEBUG: Serializer created: {serializer.__class__.__name__}")
        print(f"DEBUG: Serializer is_valid: {serializer.is_valid()}")
        
        if not serializer.is_valid():
            print(f"DEBUG: Serializer errors: {serializer.errors}")
            from rest_framework.response import Response
            from rest_framework import status
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"DEBUG: Serializer validated, calling save()")
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        print(f"DEBUG: Book created successfully, returning response")
        from rest_framework.response import Response
        from rest_framework import status
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get reviews for a specific book"""
        book = self.get_object()
        reviews = book.reviews.all()
        serializer = BookReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_review(self, request, pk=None):
        """Add a review for a book"""
        book = self.get_object()
        user_id = request.user_payload.get('user_id')
        
        serializer = BookReviewSerializer(data=request.data)
        if serializer.is_valid():
            # Check if user already reviewed this book
            existing_review = BookReview.objects.filter(book=book, user_id=user_id).first()
            if existing_review:
                # Update existing review
                existing_review.rating = serializer.validated_data['rating']
                existing_review.review_text = serializer.validated_data.get('review_text', '')
                existing_review.save()
                
                # Update book rating
                self._update_book_rating(book)
                
                return Response(BookReviewSerializer(existing_review).data)
            else:
                # Create new review
                serializer.save(book=book, user_id=user_id)
                
                # Update book rating
                self._update_book_rating(book)
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _update_book_rating(self, book):
        """Update book's average rating"""
        avg_rating = book.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        if avg_rating:
            book.rating = round(avg_rating, 2)
            book.rating_count = book.reviews.count()
            book.save()


class PDFMetadataExtractionView(APIView):
    """
    Extract metadata from uploaded PDF file
    """
    permission_classes = [IsStaffUser]
    
    def post(self, request):
        try:
            pdf_file = request.FILES.get('pdf_file')
            if not pdf_file:
                return Response({'error': 'No PDF file provided'}, status=400)
            
            if not pdf_file.name.lower().endswith('.pdf'):
                return Response({'error': 'File must be a PDF'}, status=400)
            
            metadata = {}
            
            try:
                # Extract PDF metadata using PyPDF2
                import PyPDF2
                import io
                
                # Read the PDF file
                pdf_content = pdf_file.read()
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
                
                # Extract basic metadata
                if pdf_reader.metadata:
                    metadata.update({
                        'title': pdf_reader.metadata.get('/Title', '').strip(),
                        'author': pdf_reader.metadata.get('/Author', '').strip(),
                        'subject': pdf_reader.metadata.get('/Subject', '').strip(),
                        'creator': pdf_reader.metadata.get('/Creator', '').strip(),
                        'producer': pdf_reader.metadata.get('/Producer', '').strip(),
                    })
                
                # Extract page count
                metadata['pages'] = len(pdf_reader.pages)
                
                # Try to extract some text content for description
                try:
                    # Get first page text
                    first_page = pdf_reader.pages[0]
                    text = first_page.extract_text()
                    
                    # Clean up text and use as description (first 500 chars)
                    if text:
                        cleaned_text = ' '.join(text.split())  # Remove extra whitespace
                        metadata['description'] = cleaned_text[:500] + ('...' if len(cleaned_text) > 500 else '')
                except Exception as e:
                    logger.warning(f"Could not extract text from PDF: {e}")
                
                # Try to extract language from metadata or content
                if not metadata.get('language'):
                    # Default to English if no language found
                    metadata['language'] = 'en'
                
                # Try to extract ISBN from text content
                try:
                    import re
                    # Look for ISBN patterns
                    isbn_pattern = r'(?:ISBN[-\s]*:?[\s]*)?(97[89][\d-]{10,}|\d[\d-]{9}[\dXx])'
                    matches = re.findall(isbn_pattern, text if 'text' in locals() else '')
                    if matches:
                        # Clean up ISBN (remove dashes and spaces)
                        isbn = re.sub(r'[-\s]', '', matches[0])
                        metadata['isbn'] = isbn
                except Exception as e:
                    logger.warning(f"Could not extract ISBN from PDF: {e}")
                
                # Try to extract publication date
                if not metadata.get('publication_date') and pdf_reader.metadata:
                    # Try to extract date from metadata
                    creation_date = pdf_reader.metadata.get('/CreationDate', '')
                    if creation_date:
                        try:
                            # PDF dates are in format D:YYYYMMDDHHmmSSOHH'mm'
                            date_str = creation_date[2:10]  # Extract YYYYMMDD
                            if len(date_str) == 8:
                                year = date_str[:4]
                                month = date_str[4:6]
                                day = date_str[6:8]
                                metadata['publication_date'] = f"{year}-{month}-{day}"
                        except Exception as e:
                            logger.warning(f"Could not parse PDF date: {e}")
                
                # Clean up metadata (remove empty values)
                cleaned_metadata = {k: v for k, v in metadata.items() if v and v.strip()}
                
                logger.info(f"✅ PDF metadata extracted: {cleaned_metadata}")
                return Response({'metadata': cleaned_metadata})
                
            except Exception as e:
                logger.error(f"Error extracting PDF metadata: {e}")
                return Response({'error': f'Failed to extract PDF metadata: {str(e)}'}, status=500)
                
        except Exception as e:
            logger.error(f"Unexpected error in PDF extraction: {e}")
            return Response({'error': 'Unexpected error occurred'}, status=500)


class PDFStreamingView(APIView):
    """
    Stream PDF files with range request support and authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, book_id):
        try:
            # Get book and verify access
            book = get_object_or_404(Book, id=book_id)
            
            # Check if user has access to this book
            user_id = None
            is_admin = False
            
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = request.user.id
                is_admin = request.user.is_staff or request.user.is_superuser
            elif hasattr(request, 'user_payload') and 'user_id' in request.user_payload:
                user_id = request.user_payload['user_id']
                # Check admin status from JWT payload
                is_admin = request.user_payload.get('is_staff', False) or request.user_payload.get('is_superuser', False)
            
            # Admin users have access to all books
            if not is_admin:
                if not UserLibrary.objects.filter(
                    user_id=user_id,
                    book=book,
                    is_active=True
                ).exists():
                    return HttpResponseNotFound(
                        "You don't have access to this book. Please purchase it first.",
                        content_type="text/plain"
                    )
            
            # Get PDF file path
            if not book.pdf_file:
                logger.warning(f"Book {book_id} ({book.title}) has no PDF file")
                return HttpResponseNotFound(
                    "PDF file not available for this book.",
                    content_type="text/plain"
                )
            
            pdf_path = book.pdf_file.path
            
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                return HttpResponseNotFound(
                    "PDF file not found on server.",
                    content_type="text/plain"
                )
            
            # Get file size
            file_size = os.path.getsize(pdf_path)
            
            # Handle range requests for streaming
            range_header = request.META.get('HTTP_RANGE', '').strip()
            
            if range_header:
                # Parse range header: "bytes=0-1024"
                try:
                    range_match = range_header.replace('bytes=', '').split('-')
                    start = int(range_match[0]) if range_match[0] else 0
                    end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else file_size - 1
                    
                    # Validate range
                    if start >= file_size or end >= file_size or start > end:
                        return HttpResponse(
                            "Requested Range Not Satisfiable",
                            status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                            headers={
                                'Content-Range': f'bytes */{file_size}'
                            }
                        )
                    
                    # Read the requested range
                    with open(pdf_path, 'rb') as f:
                        f.seek(start)
                        data = f.read(end - start + 1)
                    
                    # Return partial content
                    response = HttpResponse(
                        data,
                        content_type='application/pdf',
                        status=status.HTTP_206_PARTIAL_CONTENT,
                        headers={
                            'Content-Range': f'bytes {start}-{end}/{file_size}',
                            'Accept-Ranges': 'bytes',
                            'Content-Length': str(len(data)),
                            'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                            'Content-Disposition': f'inline; filename="{smart_str(book.title)}.pdf"',
                            'X-Content-Type-Options': 'nosniff',
                            'X-Frame-Options': 'SAMEORIGIN',  # Prevent embedding in other sites
                        }
                    )
                    
                    logger.info(f"PDF range request: {book.title} - bytes {start}-{end}/{file_size}")
                    return response
                    
                except (ValueError, IndexError) as e:
                    logger.error(f"Invalid range request: {range_header}, error: {e}")
                    return HttpResponse(
                        "Invalid range request",
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Full file request
            with open(pdf_path, 'rb') as f:
                data = f.read()
            
            response = HttpResponse(
                data,
                content_type='application/pdf',
                headers={
                    'Content-Length': str(file_size),
                    'Accept-Ranges': 'bytes',
                    'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                    'Content-Disposition': f'inline; filename="{smart_str(book.title)}.pdf"',
                    'X-Content-Type-Options': 'nosniff',
                    'X-Frame-Options': 'SAMEORIGIN',  # Prevent embedding in other sites
                }
            )
            
            logger.info(f"PDF full request: {book.title} - {file_size} bytes")
            return response
            
        except Exception as e:
            logger.error(f"Error serving PDF: {str(e)}")
            return HttpResponse(
                "Internal server error while loading PDF.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BookProgressView(APIView):
    """
    Update reading progress for a book
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, book_id):
        try:
            book = get_object_or_404(Book, id=book_id)
            
            # Verify user has access
            user_id = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = request.user.id
            elif hasattr(request, 'user_payload') and 'user_id' in request.user_payload:
                user_id = request.user_payload['user_id']
            
            if not UserLibrary.objects.filter(
                user_id=user_id,
                book=book,
                is_active=True
            ).exists():
                return Response(
                    {"error": "You don't have access to this book"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get progress data
            page = request.data.get('page', 1)
            progress_percentage = request.data.get('progress_percentage', 0)
            
            # Update or create progress (you might want to use a Progress model)
            # For now, just log it
            logger.info(f"Progress update: User {user_id}, Book {book.title}, Page {page}, Progress {progress_percentage}%")
            
            return Response({
                "success": True,
                "page": page,
                "progress_percentage": progress_percentage,
                "message": "Progress updated successfully"
            })
            
        except Exception as e:
            logger.error(f"Error updating progress: {str(e)}")
            return Response(
                {"error": "Failed to update progress"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
def test_public_books(request):
    """Test endpoint for public books access"""
    print(f"just DEBUG: test_public_books called for {request.path}")
    print(f"just DEBUG: Request method: {request.method}")
    print(f"just DEBUG: Request user: {getattr(request, 'user', 'No user')}")
    print(f"just DEBUG: Request user_payload: {getattr(request, 'user_payload', 'No user_payload')}")
    
    from .models import Book
    books = Book.objects.all()[:5]  # Limit to 5 for testing
    data = []
    for book in books:
        data.append({
            'id': book.id,
            'title': book.title,
            'author_name': book.author.name if book.author else 'Unknown',
            'price': book.price,
            'is_free': book.is_free,
            'pages': book.pages,
        })
    
    return Response(data)


class PublicBookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public ViewSet for viewing books without authentication
    """
    queryset = Book.objects.all()
    permission_classes = [AllowAny]  # Explicitly allow any access
    serializer_class = PublicBookSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categories', 'author', 'language']
    search_fields = ['title', 'subtitle', 'description', 'author__name']
    ordering_fields = ['title', 'created_at', 'price', 'rating']
