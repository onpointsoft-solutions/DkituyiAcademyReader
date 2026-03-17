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
    isbn = models.CharField(max_length=13, unique=True, blank=True, null=True)
    publication_date = models.DateField(null=True, blank=True)
    pages = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=10, default='en')
    
    # File storage
    pdf_file = models.FileField(upload_to='books/pdfs/', blank=True, null=True)
    cover_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Metadata
    file_size = models.BigIntegerField(default=0)  # in bytes
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    rating_count = models.PositiveIntegerField(default=0)
    
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
