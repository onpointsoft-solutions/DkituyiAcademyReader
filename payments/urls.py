from django.urls import path, include
from rest_framework.routers import SimpleRouter
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .views import WalletViewSet, ContentUnlockViewSet, SubscriptionViewSet
from .services import PaystackService

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

router = SimpleRouter()
router.register(r'wallet', WalletViewSet, basename='wallet')
router.register(r'content', ContentUnlockViewSet, basename='content-unlock')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('', include(router.urls)),
    path('webhook/', paystack_webhook, name='paystack_webhook'),
]
