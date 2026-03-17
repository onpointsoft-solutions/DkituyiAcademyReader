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
    
    class Meta:
        model = Book
        fields = ['id', 'title', 'subtitle', 'author_name', 'pages', 'language', 'rating', 
                  'cover_url', 'created_at']


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
