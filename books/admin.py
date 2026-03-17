from django.contrib import admin
from django.utils.html import format_html
from .models import Book, Author, Category, BookReview


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


class BookReviewInline(admin.TabularInline):
    model = BookReview
    extra = 0
    readonly_fields = ('user_id', 'created_at', 'updated_at')
    can_delete = True


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'get_categories', 'pages', 'language', 'rating', 'rating_count', 'created_at')
    list_filter = ('categories', 'language', 'publication_date', 'created_at')
    search_fields = ('title', 'subtitle', 'description', 'author__name')
    readonly_fields = ('rating', 'rating_count', 'file_size')
    inlines = [BookReviewInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subtitle', 'author', 'categories', 'isbn', 'publication_date')
        }),
        ('Content', {
            'fields': ('description', 'pages', 'language')
        }),
        ('Files', {
            'fields': ('pdf_file', 'cover_url', 'file_size')
        }),
        ('Metadata', {
            'fields': ('rating', 'rating_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_categories(self, obj):
        return ", ".join([category.name for category in obj.categories.all()])
    get_categories.short_description = 'Categories'
    
    def cover_image_preview(self, obj):
        if obj.cover_url:
            return format_html('<img src="{}" width="50" height="70" style="object-fit:cover;" />', obj.cover_url)
        return "No Cover"
    cover_image_preview.short_description = 'Cover Preview'
    
    def save_model(self, request, obj, form, change):
        # Calculate file size if PDF is uploaded
        if obj.pdf_file and not change:
            obj.file_size = obj.pdf_file.size
        super().save_model(request, obj, form, change)


# Update list_display to include cover preview
BookAdmin.list_display = ('title', 'author', 'cover_image_preview', 'get_categories', 'pages', 'language', 'rating', 'rating_count', 'created_at')


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
