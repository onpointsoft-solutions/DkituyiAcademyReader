from django.contrib import admin
from .models import PaymentPlan, Payment, BookPurchase, Subscription


@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'duration_days', 'max_books', 'is_active', 'created_at']
    list_filter = ['is_active', 'duration_days']
    search_fields = ['name', 'description']
    ordering = ['price', 'duration_days']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'plan', 'amount', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['paystack_reference']
    ordering = ['-created_at']
    readonly_fields = ['id', 'paystack_reference', 'gateway_response']


@admin.register(BookPurchase)
class BookPurchaseAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'book', 'price_paid', 'created_at']
    list_filter = ['currency', 'created_at']
    search_fields = ['book__title']
    ordering = ['-created_at']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'plan', 'start_date', 'end_date', 'is_active']
    list_filter = ['created_at']
    search_fields = ['plan__name']
    ordering = ['-created_at']
