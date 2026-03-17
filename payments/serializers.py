from rest_framework import serializers
from .models import Wallet, Transaction, PaystackPayment, Subscription, ContentUnlock

class WalletSerializer(serializers.ModelSerializer):
    """Serializer for wallet data"""
    
    class Meta:
        model = Wallet
        fields = ['user_id', 'balance', 'created_at', 'updated_at']
        read_only_fields = ['user_id', 'created_at', 'updated_at']

class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transaction data"""
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'user_id', 'transaction_type', 'amount', 'status', 
            'description', 'paystack_reference', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_id', 'created_at', 'updated_at']

class PaystackPaymentSerializer(serializers.ModelSerializer):
    """Serializer for Paystack payment data"""
    
    class Meta:
        model = PaystackPayment
        fields = [
            'id', 'user_id', 'email', 'amount', 'reference',
            'access_code', 'authorization_url', 'status',
            'response_data', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'user_id', 'created_at', 'processed_at']

class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscription data"""
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user_id', 'plan_type', 'status', 'amount_paid',
            'start_date', 'end_date', 'auto_renewal', 'is_active',
            'created_at'
        ]
        read_only_fields = ['id', 'user_id', 'created_at']

class ContentUnlockSerializer(serializers.ModelSerializer):
    """Serializer for content unlock data"""
    
    class Meta:
        model = ContentUnlock
        fields = [
            'id', 'user_id', 'book_id', 'content_type', 'content_identifier',
            'amount_paid', 'unlocked_at', 'expires_at'
        ]
        read_only_fields = ['id', 'user_id', 'unlocked_at']
