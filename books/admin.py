from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from .models import Book, Author, Category, BookReview, BookChapter, BookPage
import PyPDF2
import os


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)
    prepopulated_fields = {}  # For future slug implementation


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_date', 'created_at')
    search_fields = ('name', 'bio')
    list_filter = ('birth_date', 'created_at')
    ordering = ('name',)


class BookChapterInline(admin.TabularInline):
    model = BookChapter
    extra = 0
    fields = ['title', 'chapter_number', 'pages_count', 'content', 'is_free']
    ordering = ['chapter_number']


class BookPageInline(admin.TabularInline):
    model = BookPage
    extra = 0
    fields = ['page_number', 'content', 'word_count']
    readonly_fields = ['word_count']
    ordering = ['page_number']


class BookReviewInline(admin.TabularInline):
    model = BookReview
    extra = 0
    readonly_fields = ('user_id', 'created_at', 'updated_at')
    can_delete = True


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'price', 'is_free', 'total_pages', 'content_source', 'created_at')
    list_filter = ('content_source', 'is_free', 'categories', 'created_at')
    search_fields = ('title', 'description', 'author__name')
    readonly_fields = ('extracted_info', 'total_pages', 'rating', 'rating_count', 'file_size', 'per_page_cost')
    
    fieldsets = (
        ('Quick Add - Upload PDF', {
            'fields': ('title', 'pdf_file', 'price', 'is_free'),
            'description': 'Simply upload a PDF file and set the price. Author and other metadata will be extracted automatically.'
        }),
        ('Extracted Information', {
            'fields': ('extracted_info',),
            'classes': ('collapse',),
            'description': 'Information automatically extracted from the PDF file'
        }),
        ('Manual Override (Optional)', {
            'fields': ('author', 'subtitle', 'description', 'categories', 'isbn', 'publication_date', 'language', 'pages'),
            'classes': ('collapse',),
            'description': 'Override extracted information or add additional details'
        }),
        ('Media', {
            'fields': ('cover_url',)
        }),
        ('Advanced Options', {
            'fields': ('content_source', 'manual_content'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('rating', 'rating_count', 'file_size'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [BookChapterInline, BookReviewInline]
    
    def extracted_info(self, obj):
        """Display extracted PDF metadata"""
        if not obj.pdf_file:
            return "No PDF uploaded"
        
        info = []
        try:
            if obj.author:
                info.append(f"Author: {obj.author.name}")
            if obj.pages:
                info.append(f"Pages: {obj.pages}")
            if obj.isbn:
                info.append(f"ISBN: {obj.isbn}")
            if obj.publication_date:
                info.append(f"Publication Date: {obj.publication_date}")
            
            if info:
                return format_html('<br>'.join(info))
            else:
                return "No metadata extracted"
        except:
            return "Error reading metadata"
    extracted_info.short_description = '📋 Extracted from PDF'
    
    def total_pages(self, obj):
        if obj.content_source == 'manual':
            return obj.chapters.aggregate(total=models.Sum('pages_count'))['pages_count__sum'] or 0
        return obj.pages
    total_pages.short_description = 'Total Pages'
    
    def per_page_cost(self, obj):
        if obj.is_free or obj.price <= 0:
            return "FREE"
        pages = self.total_pages(obj)
        if pages > 0:
            cost_per_page = obj.price / pages
            return f"${cost_per_page:.4f}"
        return "N/A"
    per_page_cost.short_description = 'Cost Per Page'
    
    def cover_image_preview(self, obj):
        if obj.cover_url:
            return format_html('<img src="{}" width="50" height="70" style="object-fit:cover;" />', obj.cover_url)
        return "No Cover"
    cover_image_preview.short_description = 'Cover Preview'
    
    def save_model(self, request, obj, form, change):
        # Calculate file size if PDF is uploaded
        if obj.pdf_file:
            obj.file_size = obj.pdf_file.size
            
            # Extract metadata from PDF if this is a new book or PDF changed
            if not change or 'pdf_file' in form.changed_data:
                self.extract_pdf_metadata(obj)
        
        super().save_model(request, obj, form, change)
    
    def extract_pdf_metadata(self, obj):
        """Extract metadata from PDF file"""
        try:
            if not obj.pdf_file:
                return
            
            # Get the file path
            pdf_path = obj.pdf_file.path
            if not os.path.exists(pdf_path):
                return
            
            # Open PDF and extract metadata
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract basic info
                info = pdf_reader.metadata
                
                # Update title if not set
                if not obj.title and info and info.get('/Title'):
                    obj.title = info.get('/Title', '').strip()
                
                # Extract author if not set
                if not obj.author and info and info.get('/Author'):
                    author_name = info.get('/Author', '').strip()
                    if author_name:
                        author, created = Author.objects.get_or_create(
                            name=author_name,
                            defaults={'bio': f'Author extracted from PDF: {obj.title}'}
                        )
                        obj.author = author
                
                # Extract page count
                obj.pages = len(pdf_reader.pages)
                
                # Extract ISBN if available (common in PDF metadata)
                if info:
                    # Try to find ISBN in various metadata fields
                    isbn_fields = ['/ISBN', '/Identifier', '/Subject']
                    for field in isbn_fields:
                        isbn_value = info.get(field, '')
                        if isbn_value and len(str(isbn_value).replace('-', '').replace(' ', '')) >= 10:
                            # Clean up ISBN (remove spaces and hyphens)
                            clean_isbn = str(isbn_value).replace('-', '').replace(' ', '')
                            if len(clean_isbn) >= 10:
                                obj.isbn = clean_isbn[:13]  # Take first 13 characters
                                break
                
                # Extract publication date if available
                if info and info.get('/CreationDate'):
                    # PDF dates are in format: D:YYYYMMDDHHmmSS+HH'mm'
                    date_str = info.get('/CreationDate', '')
                    if date_str.startswith('D:'):
                        try:
                            date_part = date_str[2:10]  # Extract YYYYMMDD
                            year = int(date_part[:4])
                            month = int(date_part[4:6])
                            day = int(date_part[6:8])
                            from datetime import date
                            obj.publication_date = date(year, month, day)
                        except:
                            pass  # If date parsing fails, just skip it
                
                # Extract description/subject
                if not obj.description and info:
                    description = info.get('/Subject', '') or info.get('/Keywords', '')
                    if description:
                        obj.description = str(description).strip()
                    elif not obj.description:
                        obj.description = f"A book by {obj.author.name if obj.author else 'Unknown Author'}"
                
        except Exception as e:
            print(f"Error extracting PDF metadata: {e}")
            # Don't fail the save if extraction fails
            pass


# Update list_display to include cover preview
BookAdmin.list_display = ('title', 'author', 'price', 'is_free', 'total_pages', 'content_source', 'created_at')


@admin.register(BookChapter)
class BookChapterAdmin(admin.ModelAdmin):
    list_display = ('book', 'chapter_number', 'title', 'pages_count', 'is_free', 'created_at')
    list_filter = ('is_free', 'created_at', 'book')
    search_fields = ('title', 'content', 'book__title')
    
    fieldsets = (
        ('Chapter Information', {
            'fields': ('book', 'title', 'chapter_number', 'pages_count', 'is_free')
        }),
        ('Content', {
            'fields': ('content',),
            'description': 'Enter the full content for this chapter. You can organize it into pages below for better tracking.'
        })
    )
    
    inlines = [BookPageInline]


@admin.register(BookPage)
class BookPageAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'page_number', 'word_count', 'created_at')
    list_filter = ('chapter__book', 'created_at')
    search_fields = ('content', 'chapter__title')
    
    fieldsets = (
        ('Page Information', {
            'fields': ('chapter', 'page_number')
        }),
        ('Content', {
            'fields': ('content', 'word_count'),
            'description': 'Enter the content for this specific page. Word count is calculated automatically.'
        })
    )
    
    readonly_fields = ['word_count']


@admin.register(BookReview)
class BookReviewAdmin(admin.ModelAdmin):
    list_display = ('book', 'user_id', 'rating', 'created_at', 'updated_at')
    list_filter = ('rating', 'created_at', 'book')
    search_fields = ('book__title', 'review_text')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing existing object
            return self.readonly_fields + ('book', 'user_id')
        return self.readonly_fields
