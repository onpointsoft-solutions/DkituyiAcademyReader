from rest_framework import serializers
from books.models import Book, Author
from books.serializers import BookListSerializer


class AdminBookWriteSerializer(serializers.ModelSerializer):
    """Serializer for create/update; accepts author as string (name)."""
    author = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'subtitle', 'description', 'author',
            'isbn', 'publication_date', 'pages', 'language',
            'cover_url', 'pdf_file'
        ]
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'subtitle': {'allow_blank': True},
            'isbn': {'allow_blank': True, 'allow_null': True},
            'publication_date': {'allow_null': True},
            'pages': {'required': False, 'default': 0},
            'cover_url': {'allow_blank': True, 'allow_null': True},
            'pdf_file': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        author_name = validated_data.pop('author', '') or 'Unknown'
        author, _ = Author.objects.get_or_create(name=author_name)
        validated_data['author'] = author
        validated_data.setdefault('description', 'No description')
        
        # Handle file size calculation
        if 'pdf_file' in validated_data and validated_data['pdf_file']:
            file_size = validated_data['pdf_file'].size
            validated_data['file_size'] = file_size
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        author_name = validated_data.pop('author', None)
        if author_name:
            author, _ = Author.objects.get_or_create(name=author_name)
            validated_data['author'] = author
        
        # Handle file size calculation for updates
        if 'pdf_file' in validated_data and validated_data['pdf_file']:
            file_size = validated_data['pdf_file'].size
            validated_data['file_size'] = file_size
        
        return super().update(instance, validated_data)


class AdminBookListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    cover_url = serializers.URLField(read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'subtitle', 'author_name', 'pages', 'language',
            'rating', 'cover_url', 'created_at', 'updated_at'
        ]
