from rest_framework import serializers
from .models import Book, Author, Category, BookReview


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at']


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'bio', 'birth_date', 'created_at']


class BookSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.name')
    categories = serializers.CharField(source='categories.all', read_only=True)
    rating_count = serializers.IntegerField(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    def get_file_url(self, obj):
        if obj.pdf_file:
            return obj.pdf_file.url
        return None
    
    class Meta:
        model = Book
        fields = ['id', 'title', 'subtitle', 'author', 'categories', 'description', 
                  'isbn', 'publication_date', 'pages', 'language', 'cover_url', 
                  'file_url', 'file_size', 'rating', 'rating_count', 'created_at', 'updated_at']


class BookListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    reading_progress = serializers.SerializerMethodField()
    last_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Book
        fields = ['id', 'title', 'subtitle', 'author_name', 'pages', 'language', 'rating', 
                  'cover_url', 'created_at', 'reading_progress', 'last_read']
    
    def get_reading_progress(self, obj):
        """Get reading progress for authenticated user"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_payload'):
            return 0.0
        
        user_id = request.user_payload.get('user_id')
        if not user_id:
            return 0.0
        
        try:
            from library.models import ReadingProgress
            progress = ReadingProgress.objects.get(
                user_id=user_id, 
                book=obj
            )
            return progress.progress_percentage
        except ReadingProgress.DoesNotExist:
            return 0.0
    
    def get_last_read(self, obj):
        """Get last read date for authenticated user"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_payload'):
            return None
        
        user_id = request.user_payload.get('user_id')
        if not user_id:
            return None
        
        try:
            from library.models import ReadingProgress
            progress = ReadingProgress.objects.get(
                user_id=user_id, 
                book=obj
            )
            return progress.last_read
        except ReadingProgress.DoesNotExist:
            return None


class BookReviewSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = BookReview
        fields = ['id', 'book', 'user_id', 'rating', 'review_text', 'created_at', 'updated_at']
        read_only_fields = ['user_id', 'created_at', 'updated_at']
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
