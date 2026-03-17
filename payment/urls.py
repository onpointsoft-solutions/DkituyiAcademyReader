from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    PaymentPlanViewSet, PaymentViewSet, BookPurchaseViewSet, 
    SubscriptionViewSet, PaymentStatsViewSet
)

router = SimpleRouter()
router.register(r'plans', PaymentPlanViewSet, basename='payment-plans')
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'purchases', BookPurchaseViewSet, basename='book-purchases')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscriptions')
router.register(r'stats', PaymentStatsViewSet, basename='payment-stats')

urlpatterns = [
    path('', include(router.urls)),
]
