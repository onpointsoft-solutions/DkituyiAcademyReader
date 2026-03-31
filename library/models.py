from django.db import models
from django.utils import timezone
from books.models import Book


class UserLibrary(models.Model):
    """Model to track user's purchased/accessible books"""
    user_id = models.PositiveIntegerField()  # WordPress user ID
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='library_entries')
    purchase_date = models.DateTimeField(auto_now_add=True)
    access_expires = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    purchased = models.BooleanField(default=False)  # Track if book was purchased
    
    class Meta:
        unique_together = ['user_id', 'book']
        ordering = ['-purchase_date']
    
    def __str__(self):
        return f"User {self.user_id} - {self.book.title}"
    
    def is_access_valid(self):
        """Check if user still has access to this book"""
        if not self.is_active:
            return False
        if self.access_expires and self.access_expires < timezone.now():
            return False
        return True


class ReadingProgress(models.Model):
    """Model to track user's reading progress for each book"""
    user_id = models.PositiveIntegerField()  # WordPress user ID
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reading_progress')
    current_page = models.PositiveIntegerField(default=1)
    total_pages = models.PositiveIntegerField(default=0)
    progress_percentage = models.FloatField(default=0.0)
    last_read = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)
    reading_time_minutes = models.PositiveIntegerField(default=0)  # Total reading time in minutes
    
    class Meta:
        unique_together = ['user_id', 'book']
        ordering = ['-last_read']
    
    def __str__(self):
        return f"User {self.user_id} - {self.book.title} ({self.progress_percentage}%)"
    
    def update_progress(self, current_page, total_pages=None):
        """Update reading progress"""
        self.current_page = current_page
        if total_pages:
            self.total_pages = total_pages
        
        if self.total_pages > 0:
            self.progress_percentage = (self.current_page / self.total_pages) * 100
            self.is_completed = self.progress_percentage >= 100
        
        self.save()


class ReadingSession(models.Model):
    """Model to track individual reading sessions"""
    user_id = models.PositiveIntegerField()  # WordPress user ID
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='library_reading_sessions')
    start_page = models.PositiveIntegerField()
    end_page = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"User {self.user_id} - {self.book.title} session"
    
    def end_session(self, end_page):
        """End the reading session and calculate duration"""
        self.end_page = end_page
        self.end_time = timezone.now()
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            self.duration_minutes = int(duration.total_seconds() / 60)
        self.save()
