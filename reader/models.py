from django.db import models
from django.contrib.auth import get_user_model
from books.models import Book

User = get_user_model()

class Bookmark(models.Model):
    """User bookmarks for books"""
    user_id = models.PositiveIntegerField()
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='bookmarks')
    page_number = models.PositiveIntegerField()
    position = models.JSONField(default=dict)  # x, y coordinates for precise positioning
    title = models.CharField(max_length=200, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user_id', 'book', 'page_number', 'position']
        ordering = ['page_number']
    
    def __str__(self):
        return f"Bookmark for {self.book.title} - Page {self.page_number}"

class Highlight(models.Model):
    """User highlights in books"""
    user_id = models.PositiveIntegerField()
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='highlights')
    page_number = models.PositiveIntegerField()
    start_position = models.JSONField(default=dict)  # start x, y coordinates
    end_position = models.JSONField(default=dict)    # end x, y coordinates
    selected_text = models.TextField()
    color = models.CharField(max_length=7, default='#ffff00')  # hex color
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['page_number', 'created_at']
    
    def __str__(self):
        return f"Highlight in {self.book.title} - Page {self.page_number}"

class Note(models.Model):
    """User notes for books"""
    user_id = models.PositiveIntegerField()
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='notes')
    page_number = models.PositiveIntegerField()
    position = models.JSONField(default=dict)  # x, y coordinates
    content = models.TextField()
    color = models.CharField(max_length=7, default='#ffffff')  # hex color
    is_private = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['page_number', 'created_at']
    
    def __str__(self):
        return f"Note in {self.book.title} - Page {self.page_number}"

class ReadingSession(models.Model):
    """Track reading sessions to discourage screenshots"""
    user_id = models.PositiveIntegerField()
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='annotation_reading_sessions')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    pages_read = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=0)
    device_info = models.JSONField(default=dict, blank=True)
    screenshot_attempts = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"Reading session for {self.book.title} by User {self.user_id}"

class ScreenshotWarning(models.Model):
    """Track screenshot warnings for users"""
    user_id = models.PositiveIntegerField()
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='screenshot_warnings')
    warning_count = models.PositiveIntegerField(default=0)
    last_warning = models.DateTimeField(auto_now=True)
    is_blocked = models.BooleanField(default=False)
    message = models.TextField(default="Screenshots are disabled to protect author copyright. Please respect intellectual property rights.")
    
    class Meta:
        unique_together = ['user_id', 'book']
    
    def __str__(self):
        return f"Screenshot warnings for User {self.user_id} - {self.book.title}"
