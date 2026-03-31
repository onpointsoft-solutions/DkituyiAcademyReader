from rest_framework import serializers
from .models import Book, Author, Category, BookReview
import logging

logger = logging.getLogger(__name__)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at']


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'bio', 'birth_date', 'created_at']


class BookSerializer(serializers.ModelSerializer):
    author = serializers.CharField(write_only=True, required=True)
    author_name = serializers.CharField(source='author.name', read_only=True)
    categories = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    categories_display = serializers.StringRelatedField(source='categories', many=True, read_only=True)
    rating_count = serializers.IntegerField(read_only=True)
    file_url = serializers.SerializerMethodField()
    per_page_cost = serializers.SerializerMethodField()
    
    def get_file_url(self, obj):
        if obj.pdf_file:
            return obj.pdf_file.url
        return None
    
    def get_per_page_cost(self, obj):
        """Calculate cost per page for the book"""
        if obj.is_free or not obj.price or obj.price <= 0:
            return 0.00
        if obj.pages and obj.pages > 0:
            return round(float(obj.price) / int(obj.pages), 4)
        return 0.00
    
    def create(self, validated_data):
        """Handle book creation with author and categories"""
        print(f"DEBUG: BookSerializer.create called with data: {validated_data}")
        
        # Extract author name
        author_name = validated_data.pop('author', None)
        categories_data = validated_data.pop('categories', [])
        
        print(f"DEBUG: Extracted author_name: {author_name}")
        print(f"DEBUG: Extracted categories: {categories_data}")
        
        # Create or get author
        if author_name:
            author, created = Author.objects.get_or_create(
                name=author_name,
                defaults={'bio': ''}
            )
            validated_data['author'] = author
            print(f"DEBUG: Author created/updated: {author.name}, created: {created}")
        
        # Extract PDF metadata if file is provided
        pdf_file = validated_data.get('pdf_file')
        if pdf_file and not validated_data.get('pages'):
            try:
                # Extract page count from PDF
                import PyPDF2
                with pdf_file.open('rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    validated_data['pages'] = len(pdf_reader.pages)
                    
                    # Try to extract title from PDF metadata
                    if pdf_reader.metadata and not validated_data.get('title'):
                        pdf_title = pdf_reader.metadata.get('/Title', '').strip()
                        if pdf_title:
                            validated_data['title'] = pdf_title
                            
            except Exception as e:
                logger.warning(f"Could not extract PDF metadata: {e}")
        
        # Create book
        print(f"DEBUG: Creating book with data: {validated_data}")
        book = Book.objects.create(**validated_data)
        print(f"DEBUG: Book created successfully: {book.id} - {book.title}")
        
        # Handle categories
        if categories_data:
            for category_name in categories_data:
                category, created = Category.objects.get_or_create(
                    name=category_name.strip(),
                    defaults={'description': ''}
                )
                book.categories.add(category)
                print(f"DEBUG: Added category: {category.name}, created: {created}")
        
        # Auto-add book to admin user's library for testing
        try:
            from django.contrib.auth import get_user_model
            from library.models import UserLibrary, ReadingProgress
            User = get_user_model()
            
            # Get admin user (vincentAdmin)
            admin_user = User.objects.filter(username='vincentAdmin').first()
            if admin_user:
                # Add to admin's library
                UserLibrary.objects.get_or_create(
                    user_id=admin_user.id,
                    book=book,
                    defaults={'purchased': True, 'is_active': True}
                )
                
                # Create initial reading progress
                ReadingProgress.objects.get_or_create(
                    user_id=admin_user.id,
                    book=book,
                    defaults={
                        'current_page': 1,
                        'total_pages': book.pages or 0,
                        'progress_percentage': 0.0
                    }
                )
                
                logger.info(f"Book '{book.title}' added to admin library with progress tracking")
        except Exception as e:
            logger.warning(f"Could not add book to admin library: {e}")
        
        print(f"DEBUG: BookSerializer.create completed successfully")
        return book
    
    class Meta:
        model = Book
        fields = ['id', 'title', 'subtitle', 'author', 'author_name', 'categories', 'categories_display',
                  'description', 'isbn', 'publication_date', 'pages', 'language', 
                  'cover_image', 'cover_url', 'pdf_file', 'file_url', 'file_size', 
                  'rating', 'rating_count', 'price', 'is_free', 'per_page_cost', 
                  'content_source', 'manual_content', 'created_at', 'updated_at']
        extra_kwargs = {
            'pdf_file': {'required': False, 'write_only': True},
            'cover_image': {'required': False, 'write_only': True},
            'manual_content': {'required': False, 'write_only': True},
        }


class BookListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    reading_progress = serializers.SerializerMethodField()
    last_read = serializers.SerializerMethodField()
    cover_display_url = serializers.SerializerMethodField()
    per_page_cost = serializers.SerializerMethodField()
    
    class Meta:
        model = Book
        fields = ['id', 'title', 'subtitle', 'author_name', 'pages', 'language', 'rating', 
                  'cover_url', 'cover_display_url', 'per_page_cost', 'created_at', 'reading_progress', 'last_read']
    
    def get_cover_display_url(self, obj):
        """Get cover URL, preferring uploaded image over external URL"""
        if obj.cover_image:
            return obj.cover_image.url
        elif obj.cover_url:
            return obj.cover_url
        return None
    
    def get_per_page_cost(self, obj):
        """Calculate cost per page for the book"""
        if obj.is_free or obj.price <= 0:
            return 0.00
        if obj.pages and obj.pages > 0:
            return round(float(obj.price) / int(obj.pages), 4)
        return 0.00
    
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


class PublicBookSerializer(serializers.ModelSerializer):
    """Public book serializer that doesn't require authentication"""
    author_name = serializers.CharField(source='author.name', read_only=True)
    cover_display_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'subtitle', 'description', 'author_name', 
            'cover_url', 'cover_display_url', 'isbn', 'pages', 
            'language', 'price', 'is_free', 'rating', 'rating_count',
            'created_at', 'categories'
        ]
    
    def get_cover_display_url(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return obj.cover_url if obj.cover_url else None
