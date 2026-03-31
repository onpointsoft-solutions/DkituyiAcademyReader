from rest_framework import serializers
from books.models import Book, Author
from books.serializers import BookListSerializer
import PyPDF2
import os
from datetime import datetime


class AdminBookWriteSerializer(serializers.ModelSerializer):
    """Serializer for create/update; accepts author as string (name)."""
    author = serializers.CharField(write_only=True, required=False, allow_blank=True)
    author_name = serializers.CharField(source='author.name', read_only=True)
    author_bio = serializers.CharField(write_only=True, required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    is_free = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'subtitle', 'description', 'author', 'author_name', 'author_bio',
            'isbn', 'publication_date', 'pages', 'language',
            'cover_image', 'cover_url', 'pdf_file', 'price', 'is_free'
        ]
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'subtitle': {'allow_blank': True},
            'isbn': {'allow_blank': True, 'allow_null': True},
            'publication_date': {'allow_null': True},
            'pages': {'required': False, 'default': 0},
            'cover_url': {'allow_blank': True, 'allow_null': True},
            'cover_image': {'required': False, 'allow_null': True},
            'pdf_file': {'required': False, 'allow_null': True},
            'title': {'required': False, 'allow_blank': True},  # Make optional for auto-extraction
        }

    def clean_isbn(self, isbn):
        """Clean ISBN by removing hyphens, spaces, and other non-digit characters except X"""
        if not isbn:
            return None
        
        # Remove common prefixes and separators
        isbn = str(isbn).upper()
        prefixes_to_remove = ['ISBN:', 'ISBN-', 'ISBN ', 'ISBN']
        for prefix in prefixes_to_remove:
            if isbn.startswith(prefix):
                isbn = isbn[len(prefix):]
        
        # Remove hyphens, spaces, and other separators
        isbn = isbn.replace('-', '').replace(' ', '').replace('.', '').replace('_', '')
        
        # Keep only digits and X (for ISBN-10)
        cleaned_isbn = ''.join(c for c in isbn if c.isdigit() or c == 'X')
        
        # Validate ISBN format
        if len(cleaned_isbn) in [10, 13]:
            return cleaned_isbn
        
        return None

    def extract_pdf_metadata(self, pdf_file):
        """Extract metadata from PDF file with enhanced accuracy"""
        try:
            if not pdf_file:
                return {}
            
            # Handle both in-memory and file-based PDFs
            import io
            
            # Read file content
            if hasattr(pdf_file, 'path') and pdf_file.path:
                # File is saved to disk
                with open(pdf_file.path, 'rb') as file:
                    pdf_content = file.read()
            else:
                # File is in memory (uploaded via HTTP)
                pdf_content = pdf_file.read()
                # Reset file pointer for future reads
                pdf_file.seek(0)
            
            metadata = {}
            
            # Open PDF from bytes
            with io.BytesIO(pdf_content) as pdf_bytes:
                pdf_reader = PyPDF2.PdfReader(pdf_bytes)
                info = pdf_reader.metadata
                
                # Extract title with better validation
                if info and info.get('/Title'):
                    title = info.get('/Title', '').strip()
                    if len(title) > 0 and len(title) <= 200:  # Validate title length
                        metadata['title'] = title
                
                # Extract author with better validation
                if info and info.get('/Author'):
                    author_name = info.get('/Author', '').strip()
                    if len(author_name) > 0 and len(author_name) <= 100:  # Validate author length
                        metadata['author_name'] = author_name
                        
                        # Generate comprehensive author bio
                        metadata['author_bio'] = f"{author_name} is an author whose work was automatically extracted from PDF metadata. This author information was pulled from the uploaded PDF file '{metadata.get('title', 'Unknown Book')}', providing readers with insights about the creator of this content."
                
                # Extract page count with enhanced accuracy
                page_count = len(pdf_reader.pages)
                if page_count > 0:
                    metadata['pages'] = page_count
                
                # Extract ISBN with enhanced validation
                if info:
                    isbn_fields = ['/ISBN', '/Identifier', '/Subject', '/Keywords']
                    for field in isbn_fields:
                        isbn_value = info.get(field, '')
                        if isbn_value:
                            cleaned_isbn = self.clean_isbn(isbn_value)
                            if cleaned_isbn:
                                metadata['isbn'] = cleaned_isbn
                                break
                
                # Extract publication date with better parsing
                if info and info.get('/CreationDate'):
                    date_str = info.get('/CreationDate', '')
                    if date_str.startswith('D:'):
                        try:
                            # PDF dates are in format: D:YYYYMMDDHHmmSS+HH'mm'
                            date_part = date_str[2:10]
                            if len(date_part) == 8 and date_part.isdigit():
                                year = int(date_part[:4])
                                month = int(date_part[4:6])
                                day = int(date_part[6:8])
                                
                                # Validate date ranges
                                if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                                    metadata['publication_date'] = datetime(year, month, day).date()
                        except (ValueError, TypeError):
                            pass  # If date parsing fails, skip it
                
                # Extract description/subject with better validation
                if info:
                    # Try multiple fields for description
                    description_fields = ['/Subject', '/Keywords', '/Comments', '/Producer', '/Creator']
                    for field in description_fields:
                        description = info.get(field, '')
                        if description:
                            desc_text = str(description).strip()
                            # Validate description length
                            if len(desc_text) > 10 and len(desc_text) <= 1000:
                                metadata['description'] = desc_text
                                break
                
                # Extract language if available
                if info and info.get('/Language'):
                    lang = info.get('/Language', '').strip()
                    if len(lang) >= 2 and len(lang) <= 10:
                        metadata['language'] = lang[:10]  # Ensure it fits model field
                
                # Extract additional metadata for comprehensive book details
                if info:
                    # Extract publisher
                    publisher = info.get('/Producer', '') or info.get('/Creator', '')
                    if publisher and len(publisher.strip()) > 0:
                        metadata['publisher'] = publisher.strip()
                    
                    # Extract subject tags
                    subject = info.get('/Subject', '')
                    if subject and len(subject.strip()) > 0:
                        metadata['subject_tags'] = subject.strip()
                    
                    # Extract creation/modification info
                    mod_date = info.get('/ModDate', '')
                    if mod_date and mod_date.startswith('D:'):
                        try:
                            mod_part = mod_date[2:10]
                            if len(mod_part) == 8 and mod_part.isdigit():
                                year = int(mod_part[:4])
                                month = int(mod_part[4:6])
                                day = int(mod_part[6:8])
                                if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                                    metadata['modified_date'] = datetime(year, month, day).date()
                        except (ValueError, TypeError):
                            pass
                
                # Set content source
                metadata['content_source'] = 'pdf'
                
                # Extract PDF-specific properties
                try:
                    # Get first page info for cover detection
                    if len(pdf_reader.pages) > 0:
                        first_page = pdf_reader.pages[0]
                        if hasattr(first_page, 'mediabox'):
                            # Calculate page dimensions
                            mediabox = first_page.mediabox
                            if mediabox:
                                width = mediabox[2] - mediabox[0]
                                height = mediabox[3] - mediabox[1]
                                metadata['page_width'] = round(width, 2)
                                metadata['page_height'] = round(height, 2)
                                
                                # Detect if first page might be a cover (larger than typical pages)
                                if len(pdf_reader.pages) > 1:
                                    second_page = pdf_reader.pages[1]
                                    if hasattr(second_page, 'mediabox'):
                                        second_mediabox = second_page.mediabox
                                        if second_mediabox:
                                            second_width = second_mediabox[2] - second_mediabox[0]
                                            second_height = second_mediabox[3] - second_mediabox[1]
                                            
                                            # First page is likely cover if significantly different
                                            if (abs(float(width) - float(second_width)) > float(width) * 0.2 or 
                                                abs(float(height) - float(second_height)) > float(height) * 0.2):
                                                metadata['has_cover_page'] = True
                                                metadata['cover_page_number'] = 1
                except Exception as e:
                    print(f"Error extracting page dimensions: {e}")
            
            return metadata
            
        except Exception as e:
            print(f"Error extracting PDF metadata: {e}")
            return {}

    def create(self, validated_data):
        # Extract PDF metadata if PDF file is provided
        pdf_file = validated_data.get('pdf_file')
        if pdf_file:
            extracted_metadata = self.extract_pdf_metadata(pdf_file)
            
            # Use extracted metadata if fields are not provided
            if not validated_data.get('title') and extracted_metadata.get('title'):
                validated_data['title'] = extracted_metadata['title']
            
            # Use filename as title if still no title
            if not validated_data.get('title'):
                validated_data['title'] = pdf_file.name.replace('.pdf', '').replace('_', ' ').title()
            
            # Handle author
            author_name = validated_data.pop('author', '') or extracted_metadata.get('author_name', '') or 'Unknown Author'
            author_bio = validated_data.pop('author_bio', '') or extracted_metadata.get('author_bio', '') or f"Author extracted from PDF metadata for the book \"{validated_data.get('title', 'Unknown Book')}\. This author information was automatically pulled from the PDF file during book upload."
            
            author, created = Author.objects.get_or_create(
                name=author_name,
                defaults={
                    'bio': author_bio,
                }
            )
            
            # Update author bio if author already exists and new bio is provided
            if not created and author_bio:
                author.bio = author_bio
                author.save()
            
            validated_data['author'] = author
            
            # Apply other extracted metadata
            if not validated_data.get('description') and extracted_metadata.get('description'):
                validated_data['description'] = extracted_metadata['description']
            elif not validated_data.get('description'):
                validated_data['description'] = f"A compelling book by {author.name}"
            
            if not validated_data.get('pages') and extracted_metadata.get('pages'):
                validated_data['pages'] = extracted_metadata['pages']
            
            if not validated_data.get('isbn') and extracted_metadata.get('isbn'):
                validated_data['isbn'] = extracted_metadata['isbn']
            elif validated_data.get('isbn'):
                # Clean the ISBN if provided manually
                cleaned_isbn = self.clean_isbn(validated_data['isbn'])
                if cleaned_isbn:
                    validated_data['isbn'] = cleaned_isbn
                else:
                    # Remove invalid ISBN
                    validated_data.pop('isbn', None)
            
            if not validated_data.get('publication_date') and extracted_metadata.get('publication_date'):
                validated_data['publication_date'] = extracted_metadata['publication_date']
            
            if not validated_data.get('language') and extracted_metadata.get('language'):
                validated_data['language'] = extracted_metadata['language']
            
            # Store additional metadata in description or as separate fields
            if extracted_metadata.get('publisher') and not validated_data.get('description'):
                publisher_info = f"Published by {extracted_metadata['publisher']}"
                if validated_data.get('description'):
                    validated_data['description'] = f"{validated_data['description']}. {publisher_info}"
                else:
                    validated_data['description'] = publisher_info
            
            # Add subject tags to description if available
            if extracted_metadata.get('subject_tags'):
                tags_info = f"Tags: {extracted_metadata['subject_tags']}"
                if validated_data.get('description'):
                    validated_data['description'] = f"{validated_data['description']}. {tags_info}"
                else:
                    validated_data['description'] = tags_info
            
            # Set content source
            validated_data['content_source'] = 'pdf'
            
            # Handle file size calculation
            file_size = pdf_file.size
            validated_data['file_size'] = file_size
        else:
            # No PDF file, handle author manually
            author_name = validated_data.pop('author', '') or 'Unknown Author'
            author_bio = validated_data.pop('author_bio', '') or 'No bio available'
            
            author, created = Author.objects.get_or_create(
                name=author_name,
                defaults={'bio': author_bio}
            )
            
            # Update author bio if author already exists and new bio is provided
            if not created and author_bio:
                author.bio = author_bio
                author.save()
                
            validated_data['author'] = author
            validated_data.setdefault('description', 'No description')
        
        # Ensure required fields have defaults
        validated_data.setdefault('description', 'A book for readers')
        validated_data.setdefault('pages', 0)
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Extract PDF metadata if new PDF file is provided
        pdf_file = validated_data.get('pdf_file')
        if pdf_file:
            extracted_metadata = self.extract_pdf_metadata(pdf_file)
            
            # Use extracted metadata if fields are not provided
            if not validated_data.get('title') and extracted_metadata.get('title'):
                validated_data['title'] = extracted_metadata['title']
            
            # Handle author
            author_name = validated_data.pop('author', None)
            author_bio = validated_data.pop('author_bio', None)
            
            if author_name:
                author, created = Author.objects.get_or_create(
                    name=author_name,
                    defaults={'bio': author_bio or ''}
                )
                
                # Update author bio if author already exists and new bio is provided
                if not created and author_bio:
                    author.bio = author_bio
                    author.save()
                    
                validated_data['author'] = author
            elif extracted_metadata.get('author_name'):
                author, created = Author.objects.get_or_create(
                    name=extracted_metadata['author_name'],
                    defaults={'bio': extracted_metadata.get('author_bio', '')}
                )
                validated_data['author'] = author
            
            # Apply other extracted metadata if not already set
            if not validated_data.get('description') and extracted_metadata.get('description'):
                validated_data['description'] = extracted_metadata['description']
            
            if not validated_data.get('pages') and extracted_metadata.get('pages'):
                validated_data['pages'] = extracted_metadata['pages']
            
            if not validated_data.get('isbn') and extracted_metadata.get('isbn'):
                validated_data['isbn'] = extracted_metadata['isbn']
            
            # Handle file size calculation
            file_size = pdf_file.size
            validated_data['file_size'] = file_size
        else:
            # No new PDF file, handle author manually
            author_name = validated_data.pop('author', None)
            if author_name:
                author, _ = Author.objects.get_or_create(name=author_name)
                validated_data['author'] = author
        
        return super().update(instance, validated_data)


class AdminBookListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    cover_url = serializers.URLField(read_only=True)
    cover_image = serializers.ImageField(read_only=True)
    cover_display_url = serializers.SerializerMethodField()
    per_page_cost = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'subtitle', 'author_name', 'pages', 'language',
            'rating', 'cover_url', 'cover_image', 'cover_display_url', 'price', 'is_free', 'per_page_cost',
            'created_at', 'updated_at'
        ]
    
    def get_cover_display_url(self, obj):
        """Get the cover URL, preferring uploaded image over external URL"""
        if obj.cover_image:
            return obj.cover_image.url
        elif obj.cover_url:
            return obj.cover_url
        return None
    
    def get_per_page_cost(self, obj):
        """Calculate cost per page for the book"""
        if obj.is_free or not obj.price or obj.price <= 0:
            return 0.00
        if obj.pages and obj.pages > 0:
            # Ensure proper type conversion
            price = float(obj.price)
            pages = int(obj.pages)
            return round(price / pages, 4)
        return 0.00
