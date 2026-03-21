from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from payments.services import PaystackService
from payments.models import Wallet, PaystackPayment
from django.db import connection
from django.core.management import call_command

@csrf_exempt
@api_view(['GET'])
def payment_health_check(request):
    """Health check for payment system"""
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Test PaystackService initialization
        paystack_service = PaystackService()
        
        # Test model creation (optional)
        wallet_count = Wallet.objects.count()
        payment_count = PaystackPayment.objects.count()
        
        # Check environment variables
        import django.conf as settings
        paystack_key = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
        callback_url = getattr(settings, 'PAYSTACK_CALLBACK_URL', None)
        
        health_status = {
            'status': 'healthy',
            'timestamp': django.utils.timezone.now().isoformat(),
            'database': 'connected',
            'models': {
                'wallet_records': wallet_count,
                'payment_records': payment_count
            },
            'services': {
                'paystack_service': 'initialized',
                'paystack_key_configured': bool(paystack_key),
                'callback_url_configured': bool(callback_url)
            },
            'endpoints': {
                'wallet_topup': '/api/payments/wallet/topup/',
                'payment_verify': '/api/payments/verify-payment/',
                'payment_callback': '/api/payments/callback/',
                'payment_webhook': '/api/payments/webhook/'
            },
            'simulation_mode': {
                'available': True,
                'description': 'Set simulation_mode=true in verify-payment request'
            }
        }
        
        return JsonResponse(health_status)
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'timestamp': django.utils.timezone.now().isoformat(),
            'error': str(e)
        }, status=500)

@csrf_exempt
@api_view(['POST'])
def test_simulation_mode(request):
    """Test endpoint for simulation mode"""
    try:
        # Get test data
        email = request.data.get('email', 'test@example.com')
        amount = request.data.get('amount', 100)
        
        # Initialize payment
        paystack_service = PaystackService()
        result = paystack_service.initialize_transaction(email, amount, 1)
        
        if result['success']:
            # Verify in simulation mode
            verify_result = paystack_service.verify_transaction(result['reference'])
            
            return JsonResponse({
                'status': 'success',
                'test_completed': True,
                'payment_initialized': result,
                'payment_verified': verify_result,
                'simulation_mode': True
            })
        else:
            return JsonResponse({
                'status': 'error',
                'test_completed': False,
                'error': result.get('error', 'Unknown error')
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'test_completed': False,
            'error': str(e)
        }, status=500)
