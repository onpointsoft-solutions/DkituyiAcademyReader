from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import requests
import json

from .models import PaymentPlan, Payment, BookPurchase, Subscription
from .serializers import PaymentPlanSerializer, PaymentSerializer, BookPurchaseSerializer, SubscriptionSerializer
from books.models import Book
from library.models import UserLibrary
from core.email import EmailService
from django.contrib.auth.models import User


class PaymentPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for payment plans"""
    queryset = PaymentPlan.objects.filter(is_active=True)
    serializer_class = PaymentPlanSerializer
    permission_classes = []


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for payment management"""
    serializer_class = PaymentSerializer
    permission_classes = []
    
    def get_queryset(self):
        user_id = self.request.user_payload.get('user_id') if self.request.user_payload else None
        if user_id:
            return Payment.objects.filter(user_id=user_id)
        return Payment.objects.none()
    
    @action(detail=False, methods=['post'])
    def initiate_payment(self, request):
        """Initiate payment with Paystack"""
        user_id = request.user_payload.get('user_id') if self.request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response(
                {'error': 'Plan ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            plan = PaymentPlan.objects.get(id=plan_id, is_active=True)
        except PaymentPlan.DoesNotExist:
            return Response(
                {'error': 'Invalid plan'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create payment record
        payment = Payment.objects.create(
            user_id=user_id,
            plan=plan,
            amount=plan.price,
            currency='USD',
            status='pending',
            expires_at=timezone.now() + timezone.timedelta(hours=24)  # 24-hour expiry
        )
        
        # Initialize Paystack payment
        try:
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'email': request.user_payload.get('user_email', 'user@example.com'),
                'amount': int(plan.price * 100),  # Convert to kobo
                'currency': plan.currency,
                'reference': str(payment.id),
                'callback_url': f"{settings.FRONTEND_URL}/payment/verify/{payment.id}",
                'metadata': {
                    'payment_id': str(payment.id),
                    'plan_id': plan.id,
                    'user_id': user_id
                }
            }
            
            response = requests.post(
                'https://api.paystack.co/transaction/initialize',
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    payment.paystack_reference = data['data']['reference']
                    payment.paystack_payment_id = data['data']['access_code']
                    payment.gateway_response = data['data']
                    payment.save()
                    
                    return Response({
                        'payment': PaymentSerializer(payment).data,
                        'authorization_url': data['data']['authorization_url'],
                        'access_code': data['data']['access_code'],
                        'reference': data['data']['reference']
                    })
                else:
                    payment.status = 'failed'
                    payment.gateway_response = data
                    payment.save()
                    return Response(
                        {'error': 'Payment initialization failed'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                payment.status = 'failed'
                payment.gateway_response = response.json()
                payment.save()
                return Response(
                    {'error': 'Payment service error'}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
        
        except Exception as e:
            payment.status = 'failed'
            payment.gateway_response = {'error': str(e)}
            payment.save()
            return Response(
                {'error': 'Payment initialization failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def verify_payment(self, request):
        """Verify payment with Paystack"""
        reference = request.data.get('reference')
        if not reference:
            return Response(
                {'error': 'Reference is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_id = request.user_payload.get('user_id') if self.request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            payment = Payment.objects.get(
                paystack_reference=reference, 
                user_id=user_id,
                status='pending'
            )
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify with Paystack
        try:
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'https://api.paystack.co/transaction/verify/{reference}',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') and data['data']['status'] == 'success':
                    payment.status = 'completed'
                    payment.gateway_response = data['data']
                    payment.save()
                    
                    # Create subscription
                    subscription = Subscription.objects.create(
                        user_id=user_id,
                        plan=payment.plan,
                        payment=payment,
                        start_date=timezone.now(),
                        end_date=timezone.now() + timezone.timedelta(days=payment.plan.duration_days)
                    )
                    
                    # Send subscription confirmation email
                    try:
                        user = User.objects.get(id=user_id)
                        EmailService.send_subscription_confirmation(
                            user_email=user.email,
                            plan_name=payment.plan.name,
                            amount=payment.amount,
                            start_date=subscription.start_date.strftime('%Y-%m-%d'),
                            end_date=subscription.end_date.strftime('%Y-%m-%d')
                        )
                    except Exception as e:
                        # Log error but don't fail the payment
                        print(f"Failed to send subscription email: {e}")
                    
                    # Add books to user library based on plan
                    if payment.plan.max_books > 0:
                        # Add some sample books to user library
                        from books.models import Book
                        books = Book.objects.all()[:payment.plan.max_books]
                        for book in books:
                            UserLibrary.objects.get_or_create(
                                user_id=user_id,
                                book=book,
                                defaults={
                                    'purchase_date': timezone.now(),
                                    'is_active': True
                                }
                            )
                    
                    return Response({
                        'payment': PaymentSerializer(payment).data,
                        'subscription': SubscriptionSerializer(subscription).data
                    })
                else:
                    payment.status = 'failed'
                    payment.gateway_response = data['data']
                    payment.save()
                    return Response(
                        {'error': 'Payment verification failed'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {'error': 'Verification service error'}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
        
        except Exception as e:
            return Response(
                {'error': 'Verification failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BookPurchaseViewSet(viewsets.ModelViewSet):
    """ViewSet for book purchases"""
    serializer_class = BookPurchaseSerializer
    permission_classes = []
    
    def get_queryset(self):
        user_id = self.request.user_payload.get('user_id') if self.request.user_payload else None
        if user_id:
            return BookPurchase.objects.filter(user_id=user_id)
        return BookPurchase.objects.none()
    
    @action(detail=False, methods=['post'])
    def purchase_book(self, request):
        """Purchase individual book"""
        user_id = request.user_payload.get('user_id') if self.request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        book_id = request.data.get('book_id')
        if not book_id:
            return Response(
                {'error': 'Book ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user already has access
        if UserLibrary.objects.filter(user_id=user_id, book=book).exists():
            return Response(
                {'error': 'You already have access to this book'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create payment for individual book purchase
        price = getattr(book, 'price', None) or 9.99  # Default price if not set
        
        payment = Payment.objects.create(
            user_id=user_id,
            plan=None,  # Individual purchase
            amount=price,
            currency='USD',
            status='pending'
        )
        
        # Initialize Paystack payment
        try:
            headers = {
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'email': request.user_payload.get('user_email', 'user@example.com'),
                'amount': int(price * 100),  # Convert to kobo
                'currency': 'USD',
                'reference': str(payment.id),
                'callback_url': f"{settings.FRONTEND_URL}/payment/verify/{payment.id}",
                'metadata': {
                    'payment_id': str(payment.id),
                    'book_id': book.id,
                    'user_id': user_id,
                    'purchase_type': 'individual_book'
                }
            }
            
            response = requests.post(
                'https://api.paystack.co/transaction/initialize',
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    payment.paystack_reference = data['data']['reference']
                    payment.paystack_payment_id = data['data']['access_code']
                    payment.gateway_response = data['data']
                    payment.save()
                    
                    return Response({
                        'payment': PaymentSerializer(payment).data,
                        'authorization_url': data['data']['authorization_url'],
                        'access_code': data['data']['access_code'],
                        'reference': data['data']['reference']
                    })
                else:
                    payment.status = 'failed'
                    payment.gateway_response = data
                    payment.save()
                    return Response(
                        {'error': 'Payment initialization failed'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                payment.status = 'failed'
                payment.gateway_response = response.json()
                payment.save()
                return Response(
                    {'error': 'Payment service error'}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
        
        except Exception as e:
            payment.status = 'failed'
            payment.gateway_response = {'error': str(e)}
            payment.save()
            return Response(
                {'error': 'Payment initialization failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user subscriptions"""
    serializer_class = SubscriptionSerializer
    permission_classes = []
    
    def get_queryset(self):
        user_id = self.request.user_payload.get('user_id') if self.request.user_payload else None
        if user_id:
            return Subscription.objects.filter(user_id=user_id)
        return Subscription.objects.none()
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get user's active subscription"""
        user_id = request.user_payload.get('user_id') if self.request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        subscription = self.get_queryset().filter(is_active=True).first()
        if subscription:
            return Response(SubscriptionSerializer(subscription).data)
        return Response({'detail': 'No active subscription'}, status=status.HTTP_404_NOT_FOUND)


class PaymentStatsViewSet(viewsets.ViewSet):
    """Payment statistics for admin"""
    permission_classes = []
    
    def list(self, request):
        """Get payment statistics"""
        user_id = request.user_payload.get('user_id') if self.request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # For now, return basic stats. In production, check for admin permissions
        total_revenue = Payment.objects.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_payments = Payment.objects.filter(status='completed').count()
        pending_payments = Payment.objects.filter(status='pending').count()
        active_subscriptions = Subscription.objects.filter(is_active=True).count()
        
        return Response({
            'total_revenue': total_revenue,
            'total_payments': total_payments,
            'pending_payments': pending_payments,
            'active_subscriptions': active_subscriptions
        })
