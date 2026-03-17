from django.db import models
from django.utils import timezone
from django.conf import settings

class Wallet(models.Model):
    """User wallet for managing reading credits"""
    user_id = models.IntegerField(unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for user {self.user_id} - KES {self.balance}"

    def add_funds(self, amount):
        """Add funds to wallet"""
        self.balance += amount
        self.save()
        return self.balance

    def deduct_funds(self, amount):
        """Deduct funds from wallet"""
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            return True
        return False

class Transaction(models.Model):
    """Transaction history for wallet operations"""
    TRANSACTION_TYPES = [
        ('topup', 'Top Up'),
        ('unlock_chapter', 'Unlock Chapter'),
        ('unlock_section', 'Unlock Section'),
        ('unlock_book', 'Unlock Book'),
        ('subscription', 'Subscription'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user_id = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True)
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_type} - KES {self.amount} for user {self.user_id}"

class PaystackPayment(models.Model):
    """Paystack payment records"""
    user_id = models.IntegerField()
    email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    access_code = models.CharField(max_length=100, blank=True, null=True)
    authorization_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    response_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Paystack payment {self.reference} - KES {self.amount}"

class ContentUnlock(models.Model):
    """Track unlocked content for users"""
    CONTENT_TYPES = [
        ('chapter', 'Chapter'),
        ('section', 'Section'),
        ('book', 'Book'),
    ]
    
    user_id = models.IntegerField()
    book_id = models.IntegerField()
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    content_identifier = models.CharField(max_length=100)  # chapter number, section name, etc.
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)  # For subscription-based access

    class Meta:
        unique_together = ['user_id', 'book_id', 'content_type', 'content_identifier']

    def __str__(self):
        return f"{self.content_type} {self.content_identifier} unlocked for user {self.user_id}"

class Subscription(models.Model):
    """User subscription plans"""
    PLAN_TYPES = [
        ('weekly', 'Weekly Unlimited'),
        ('monthly', 'Monthly Unlimited'),
        ('premium', 'Premium (Books + Audio)'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user_id = models.IntegerField()
    plan_type = models.CharField(max_length=10, choices=PLAN_TYPES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    auto_renewal = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.plan_type} subscription for user {self.user_id}"

    def is_active(self):
        return self.status == 'active' and timezone.now() <= self.end_date

    def renew(self):
        """Renew subscription for another period"""
        if self.plan_type == 'weekly':
            self.end_date += timezone.timedelta(weeks=1)
        elif self.plan_type == 'monthly':
            self.end_date += timezone.timedelta(days=30)
        elif self.plan_type == 'premium':
            self.end_date += timezone.timedelta(days=30)
        self.save()
