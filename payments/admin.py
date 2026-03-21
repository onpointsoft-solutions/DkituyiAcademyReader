from django.contrib import admin
from .models import Wallet, Transaction, PaystackPayment, ContentUnlock, Subscription

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'balance', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'amount', 'transaction_type', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['user_id', 'reference']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

@admin.register(PaystackPayment)
class PaystackPaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'email', 'amount', 'reference', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user_id', 'reference', 'paystack_reference', 'email']
    readonly_fields = ['created_at', 'processed_at']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

@admin.register(ContentUnlock)
class ContentUnlockAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'content_type', 'content_identifier', 'amount_paid', 'unlocked_at']
    list_filter = ['content_type', 'unlocked_at']
    search_fields = ['user_id', 'content_identifier']
    readonly_fields = ['unlocked_at']
    ordering = ['-unlocked_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'plan_type', 'status', 'start_date', 'end_date']
    list_filter = ['plan_type', 'status', 'start_date', 'end_date']
    search_fields = ['user_id']
    readonly_fields = ['start_date', 'end_date']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
