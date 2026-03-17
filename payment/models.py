from django.db import models
from django.contrib.auth.models import User
from books.models import Book
from library.models import UserLibrary
from django.utils import timezone
import uuid


class PaymentPlan(models.Model):
    """Payment plans for accessing books"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField(help_text="Duration in days")
    max_books = models.PositiveIntegerField(help_text="Maximum number of books")
    features = models.JSONField(default=list, help_text="List of features")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - ${self.price}/{self.duration_days} days"
    
    class Meta:
        ordering = ['price', 'duration_days']


class Payment(models.Model):
    """Payment records for user purchases"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    plan = models.ForeignKey(PaymentPlan, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    paystack_payment_id = models.CharField(max_length=100, blank=True, null=True)
    gateway_response = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Payment {self.id} by {self.user.username} - {self.plan.name}"
    
    @property
    def is_active(self):
        """Check if payment is still active"""
        if self.status != 'completed':
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True
    
    class Meta:
        ordering = ['-created_at']


class BookPurchase(models.Model):
    """Track individual book purchases"""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='book_purchases')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='purchases')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='book_purchases')
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} purchased {self.book.title}"


class Subscription(models.Model):
    """User subscription records"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(PaymentPlan, on_delete=models.CASCADE, related_name='subscriptions')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='subscriptions')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
    
    @property
    def is_active(self):
        """Check if subscription is still active"""
        if not self.is_active:
            return False
        if self.end_date and self.end_date < timezone.now():
            return False
        return True
    
    class Meta:
        ordering = ['-created_at']
