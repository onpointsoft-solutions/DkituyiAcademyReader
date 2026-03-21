from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg
from .models import Book, BookReview
from .serializers import BookSerializer, BookListSerializer, BookReviewSerializer


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing books
    """
    queryset = Book.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categories', 'author', 'language']
    search_fields = ['title', 'subtitle', 'description', 'author__name']
    ordering_fields = ['title', 'created_at', 'rating', 'publication_date']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BookListSerializer
        return BookSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
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
