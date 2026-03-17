from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Wallet, Transaction, PaystackPayment, Subscription, ContentUnlock
from .serializers import WalletSerializer, TransactionSerializer, PaystackPaymentSerializer, SubscriptionSerializer, ContentUnlockSerializer
from .services import PaystackService, WalletService

class WalletViewSet(viewsets.ViewSet):
    """
    ViewSet for wallet management
    """
    permission_classes = []  # Remove IsAuthenticated to use custom auth
    
    def get_object(self):
        """Get user wallet"""
        user_id = self.request.user_payload.get('user_id') if self.request.user_payload else None
        if not user_id:
            return None
        return WalletService.get_user_wallet(user_id)
    
    def list(self, request):
        """Get user wallet balance"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        wallet = WalletService.get_user_wallet(user_id)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def topup(self, request):
        """Initiate wallet top-up via Paystack"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        email = request.data.get('email')
        amount = request.data.get('amount')
        
        if not email or not amount:
            return Response(
                {'error': 'Email and amount are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate amount (minimum 20 KES)
        try:
            amount = float(amount)
            if amount < 20:
                return Response(
                    {'error': 'Minimum top-up amount is KES 20'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {'error': 'Invalid amount'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initiate Paystack payment
        paystack_service = PaystackService()
        result = paystack_service.initialize_transaction(
            email=email,
            amount=amount,
            user_id=user_id,
            metadata={"custom_fields": [
                {
                    "display_name": "DKT User ID",
                    "variable_name": "user_id",
                    "value": user_id
                }
            ]}
        )
        
        if result['success']:
            return Response({
                'message': 'Payment initiated successfully',
                'authorization_url': result['authorization_url'],
                'access_code': result['access_code'],
                'reference': result['reference']
            })
        else:
            return Response(
                {'error': result['error']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def verify_payment(self, request):
        """Verify Paystack payment"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        reference = request.data.get('reference')
        
        if not reference:
            return Response(
                {'error': 'Reference is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        paystack_service = PaystackService()
        result = paystack_service.verify_transaction(reference)
        
        if result['success']:
            return Response({
                'message': 'Payment verified successfully',
                'wallet_balance': WalletService.get_balance(user_id)
            })
        else:
            return Response(
                {'error': result['message']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """Get user transaction history"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        transactions = Transaction.objects.filter(user_id=user_id).order_by('-created_at')
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

class ContentUnlockViewSet(viewsets.ViewSet):
    """
    ViewSet for content unlocking
    """
    permission_classes = []  # Remove IsAuthenticated to use custom auth
    
    @action(detail=False, methods=['post'])
    def unlock_chapter(self, request):
        """Unlock a chapter"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        book_id = request.data.get('book_id')
        chapter_number = request.data.get('chapter_number')
        
        if not book_id or not chapter_number:
            return Response(
                {'error': 'Book ID and chapter number are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already unlocked
        if ContentUnlock.objects.filter(
            user_id=user_id,
            book_id=book_id,
            content_type='chapter',
            content_identifier=str(chapter_number)
        ).exists():
            return Response({
                'message': 'Chapter already unlocked',
                'unlocked': True
            })
        
        # Unlock chapter (20-30 KES per chapter)
        cost = 25  # Default chapter price
        
        result = WalletService.unlock_content(
            user_id=user_id,
            book_id=book_id,
            content_type='chapter',
            content_identifier=str(chapter_number),
            cost=cost
        )
        
        if result['success']:
            return Response({
                'message': 'Chapter unlocked successfully',
                'unlocked': True,
                'cost': cost
            })
        else:
            return Response(
                {'error': result['error']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def unlock_section(self, request):
        """Unlock a section"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        book_id = request.data.get('book_id')
        section_name = request.data.get('section_name')
        
        if not book_id or not section_name:
            return Response(
                {'error': 'Book ID and section name are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already unlocked
        if ContentUnlock.objects.filter(
            user_id=user_id,
            book_id=book_id,
            content_type='section',
            content_identifier=section_name
        ).exists():
            return Response({
                'message': 'Section already unlocked',
                'unlocked': True
            })
        
        # Unlock section (49 KES per section)
        cost = 49
        
        result = WalletService.unlock_content(
            user_id=user_id,
            book_id=book_id,
            content_type='section',
            content_identifier=section_name,
            cost=cost
        )
        
        if result['success']:
            return Response({
                'message': 'Section unlocked successfully',
                'unlocked': True,
                'cost': cost
            })
        else:
            return Response(
                {'error': result['error']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def unlock_book(self, request):
        """Unlock full book"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
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
        
        # Check if already unlocked
        if ContentUnlock.objects.filter(
            user_id=user_id,
            book_id=book_id,
            content_type='book',
            content_identifier='full_book'
        ).exists():
            return Response({
                'message': 'Book already unlocked',
                'unlocked': True
            })
        
        # Unlock full book (99-149 KES)
        cost = 129  # Default full book price
        
        result = WalletService.unlock_content(
            user_id=user_id,
            book_id=book_id,
            content_type='book',
            content_identifier='full_book',
            cost=cost
        )
        
        if result['success']:
            return Response({
                'message': 'Book unlocked successfully',
                'unlocked': True,
                'cost': cost
            })
        else:
            return Response(
                {'error': result['error']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def check_access(self, request):
        """Check if user has access to content"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        book_id = request.query_params.get('book_id')
        content_type = request.query_params.get('content_type')
        content_identifier = request.query_params.get('content_identifier')
        
        if not all([book_id, content_type, content_identifier]):
            return Response(
                {'error': 'Book ID, content type, and content identifier are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if content is unlocked
        is_unlocked = ContentUnlock.objects.filter(
            user_id=user_id,
            book_id=book_id,
            content_type=content_type,
            content_identifier=content_identifier
        ).exists()
        
        # Check if user has active subscription
        has_subscription = Subscription.objects.filter(
            user_id=user_id,
            status='active'
        ).exists()
        
        return Response({
            'has_access': is_unlocked or has_subscription,
            'is_unlocked': is_unlocked,
            'has_subscription': has_subscription
        })

class SubscriptionViewSet(viewsets.ViewSet):
    """
    ViewSet for subscription management
    """
    permission_classes = []  # Remove IsAuthenticated to use custom auth
    
    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        """Subscribe to a plan"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        plan_type = request.data.get('plan_type')
        
        if not plan_type:
            return Response(
                {'error': 'Plan type is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Plan pricing
        plan_prices = {
            'weekly': 99,
            'monthly': 299,
            'premium': 499
        }
        
        if plan_type not in plan_prices:
            return Response(
                {'error': 'Invalid plan type'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cost = plan_prices[plan_type]
        
        # Check wallet balance
        if not WalletService.can_unlock_content(user_id, cost):
            return Response(
                {'error': 'Insufficient balance'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create subscription
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now()
        if plan_type == 'weekly':
            end_date = start_date + timedelta(weeks=1)
        elif plan_type == 'monthly':
            end_date = start_date + timedelta(days=30)
        else:  # premium
            end_date = start_date + timedelta(days=30)
        
        subscription = Subscription.objects.create(
            user_id=user_id,
            plan_type=plan_type,
            amount_paid=cost,
            start_date=start_date,
            end_date=end_date
        )
        
        # Deduct from wallet
        wallet = WalletService.get_user_wallet(user_id)
        wallet.deduct_funds(cost)
        
        # Create transaction record
        Transaction.objects.create(
            user_id=user_id,
            transaction_type='subscription',
            amount=cost,
            status='completed',
            description=f"{plan_type} subscription"
        )
        
        return Response({
            'message': 'Subscription created successfully',
            'subscription': {
                'plan_type': plan_type,
                'start_date': start_date,
                'end_date': end_date,
                'amount_paid': cost
            }
        })
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current subscription"""
        user_id = request.user_payload.get('user_id') if request.user_payload else None
        if not user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        subscription = Subscription.objects.filter(
            user_id=user_id,
            status='active'
        ).first()
        
        if subscription and subscription.is_active():
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data)
        
        return Response({'subscription': None})
