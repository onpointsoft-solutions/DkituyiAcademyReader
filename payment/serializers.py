from rest_framework import serializers
from .models import PaymentPlan, Payment, BookPurchase, Subscription
from books.serializers import BookSerializer


class PaymentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPlan
        fields = ['id', 'name', 'description', 'price', 'duration_days', 'max_books', 'features', 'is_active', 'created_at']


class PaymentSerializer(serializers.ModelSerializer):
    plan = PaymentPlanSerializer(read_only=True)
    user = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'plan', 'amount', 'currency', 'status', 
            'paystack_reference', 'created_at', 'updated_at', 'expires_at'
        ]


class BookPurchaseSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    user = serializers.CharField(source='user.username', read_only=True)
    payment = PaymentSerializer(read_only=True)
    
    class Meta:
        model = BookPurchase
        fields = ['id', 'book', 'user', 'payment', 'price_paid', 'currency', 'created_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PaymentPlanSerializer(read_only=True)
    user = serializers.CharField(source='user.username', read_only=True)
    payment = PaymentSerializer(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user', 'plan', 'payment', 'start_date', 'end_date', 
            'is_active', 'created_at'
        ]
