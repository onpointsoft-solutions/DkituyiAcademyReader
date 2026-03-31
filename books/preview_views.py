from django.http import HttpResponse, Http404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from books.models import Book
from .pdf_analyzer import PDFContentAnalyzer
import io
import base64

class BookPreviewViewSet(viewsets.GenericViewSet):
    """
    ViewSet for book preview functionality with advanced content analysis
    """
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Get smart preview of book content with chapter/section detection"""
        try:
            book = Book.objects.get(id=pk)
            
            if not book.pdf_file:
                return Response(
                    {'error': 'No PDF file available for this book'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read PDF file
            pdf_content = book.pdf_file.read()
            
            # Initialize PDF analyzer
            analyzer = PDFContentAnalyzer(pdf_content)
            
            # Get smart preview pages (includes complete chapters)
            preview_pages = analyzer.get_smart_preview_pages(0.2)  # 20%
            
            # Analyze content structure
            content_analysis = analyzer.analyze_content_structure(0, len(preview_pages))
            
            # Calculate per-page cost
            per_page_cost = 0.00
            if not book.is_free and book.price > 0 and analyzer.total_pages > 0:
                per_page_cost = round(float(book.price) / analyzer.total_pages, 4)
            
            # Extract text from preview pages
            preview_text = ""
            for page_num in preview_pages:
                page_text = analyzer.extract_page_text(page_num)
                preview_text += f"--- Page {page_num + 1} ---\n"
                preview_text += page_text + "\n\n"
            
            # Limit text length for performance
            preview_text = preview_text[:5000]
            
            return Response({
                'book_id': book.id,
                'title': book.title,
                'author': book.author.name if book.author else 'Unknown',
                'total_pages': analyzer.total_pages,
                'preview_pages': len(preview_pages),
                'preview_page_numbers': preview_pages,
                'preview_text': preview_text,
                'preview_percentage': 20,
                'per_page_cost': per_page_cost,
                'cover_url': book.cover_url,
                'description': book.description,
                'requires_signup': True,
                'content_analysis': {
                    'chapters_found': len(content_analysis['chapters']),
                    'sections_found': len(content_analysis['sections']),
                    'chapters': content_analysis['chapters'][:3],  # First 3 chapters
                    'sections': content_analysis['sections'][:5],  # First 5 sections
                    'smart_preview': True
                }
            })
            
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate preview: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def content_structure(self, request, pk=None):
        """Get detailed content structure analysis"""
        try:
            book = Book.objects.get(id=pk)
            
            if not book.pdf_file:
                return Response(
                    {'error': 'No PDF file available for this book'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read PDF file
            pdf_content = book.pdf_file.read()
            
            # Initialize PDF analyzer
            analyzer = PDFContentAnalyzer(pdf_content)
            
            # Get page range from request
            start_page = int(request.GET.get('start_page', 0))
            end_page = int(request.GET.get('end_page', min(50, analyzer.total_pages)))
            
            # Analyze content structure
            content_analysis = analyzer.analyze_content_structure(start_page, end_page)
            
            # Find content boundaries
            boundaries = analyzer.find_content_boundaries(start_page, end_page - start_page)
            
            return Response({
                'book_id': book.id,
                'total_pages': analyzer.total_pages,
                'analyzed_range': {
                    'start_page': start_page,
                    'end_page': end_page
                },
                'content_analysis': content_analysis,
                'boundaries': boundaries
            })
            
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to analyze content: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def reading_progress(self, request, pk=None):
        """Get reading progress with content boundaries"""
        try:
            book = Book.objects.get(id=pk)
            
            if not book.pdf_file:
                return Response(
                    {'error': 'No PDF file available for this book'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read PDF file
            pdf_content = book.pdf_file.read()
            
            # Initialize PDF analyzer
            analyzer = PDFContentAnalyzer(pdf_content)
            
            # Get current page from request
            current_page = int(request.GET.get('current_page', 0))
            total_read_pages = int(request.GET.get('total_read_pages', current_page))
            
            # Calculate reading progress
            progress = analyzer.get_reading_progress(current_page, total_read_pages)
            
            return Response({
                'book_id': book.id,
                'progress': progress,
                'content_boundaries': analyzer.find_content_boundaries(current_page, 5)
            })
            
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to calculate progress: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
