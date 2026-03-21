from django.urls import path, include
from rest_framework.routers import SimpleRouter
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from .views import WalletViewSet, ContentUnlockViewSet, SubscriptionViewSet
from .services import PaystackService
from . import health

@csrf_exempt
def paystack_webhook(request):
    """Handle Paystack webhook"""
    if request.method == 'POST':
        try:
            webhook_data = request.data
            paystack_service = PaystackService()
            result = paystack_service.process_webhook(webhook_data)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@csrf_exempt
def payment_callback(request):
    """Handle Paystack payment callback"""
    if request.method == 'GET':
        reference = request.GET.get('reference')
        trxref = request.GET.get('trxref')
        
        if reference:
            # You can redirect to frontend or return a response
            return HttpResponse(f"""
                <html>
                <head><title>Payment Processing</title></head>
                <body>
                    <h2>Payment Received!</h2>
                    <p>Reference: {reference}</p>
                    <p>Transaction: {trxref}</p>
                    <p>Redirecting to your wallet...</p>
                    <script>
                        setTimeout(function() {{
                            window.location.href = 'https://eminently-rare-pegasus.ngrok-free.app/profile';
                        }}, 3000);
                    </script>
                </body>
                </html>
            """)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

router = SimpleRouter()
router.register(r'wallet', WalletViewSet, basename='wallet')
router.register(r'content', ContentUnlockViewSet, basename='content-unlock')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('', include(router.urls)),
    path('wallet/topup/', WalletViewSet.as_view({'post': 'topup'}), name='wallet-topup'),
    path('health/', health.payment_health_check, name='payment-health'),
    path('test-simulation/', health.test_simulation_mode, name='test-simulation'),
    path('webhook/', paystack_webhook, name='paystack_webhook'),
    path('verify-payment/', WalletViewSet.as_view({'post': 'verify_payment'}), name='verify-payment'),
    path('callback/', payment_callback, name='payment-callback'),
]
