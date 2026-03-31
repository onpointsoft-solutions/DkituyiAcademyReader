from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    description = models.TextField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    categories = models.ManyToManyField(Category, related_name='books', blank=True)
    isbn = models.CharField(max_length=13, blank=True, null=True)  # Removed unique=True for testing
    publication_date = models.DateField(null=True, blank=True)
    pages = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=10, default='en')
    
    # File storage
    pdf_file = models.FileField(upload_to='books/pdfs/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='books/covers/', blank=True, null=True)
    cover_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Content management
    content_source = models.CharField(
        max_length=20,
        choices=[
            ('pdf', 'PDF File'),
            ('manual', 'Manual Entry'),
        ],
        default='pdf'
    )
    manual_content = models.TextField(blank=True, help_text="Paste book content here if not using PDF file")
    
    # Metadata
    file_size = models.BigIntegerField(default=0)  # in bytes
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    rating_count = models.PositiveIntegerField(default=0)
    
    # Pricing for charging
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_free = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} by {self.author.name}"
    
    @property
    def file_url(self):
        if self.pdf_file:
            return self.pdf_file.url
        return None
    
    @property
    def cover_display_url(self):
        """Get the cover URL, preferring uploaded image over external URL"""
        if self.cover_image:
            return self.cover_image.url
        elif self.cover_url:
            return self.cover_url
        return None
    
    @property
    def total_pages(self):
        if self.content_source == 'manual':
            return self.chapters.aggregate(models.Sum('pages_count'))['pages_count__sum'] or 0
        return self.pages


class BookChapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200)
    chapter_number = models.PositiveIntegerField()
    pages_count = models.PositiveIntegerField(default=1)
    content = models.TextField()
    is_free = models.BooleanField(default=False, help_text="Make this chapter available for free preview")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['chapter_number']
        unique_together = ['book', 'chapter_number']
    
    def __str__(self):
        return f"Chapter {self.chapter_number}: {self.title}"


class BookPage(models.Model):
    chapter = models.ForeignKey(BookChapter, on_delete=models.CASCADE, related_name='pages')
    page_number = models.PositiveIntegerField()
    content = models.TextField()
    word_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['page_number']
        unique_together = ['chapter', 'page_number']
    
    def __str__(self):
        return f"Page {self.page_number} of {self.chapter.title}"
    
    def save(self, *args, **kwargs):
        # Count words in content
        if self.content:
            self.word_count = len(self.content.split())
        super().save(*args, **kwargs)


class BookReview(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    user_id = models.PositiveIntegerField()  # WordPress user ID
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['book', 'user_id']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.user_id} for {self.book.title}"
