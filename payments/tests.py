from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from payments.models import Wallet, PaystackPayment
from payments.services import PaystackService

User = get_user_model()

class PaymentTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        
        # Mock authentication
        self.client.credentials(
            HTTP_AUTHORIZATION='Bearer mock_token'
        )
        
    def test_wallet_topup_endpoint_exists(self):
        """Test that the wallet topup endpoint exists"""
        url = '/api/payments/wallet/topup/'
        response = self.client.post(url, {
            'email': 'test@example.com',
            'amount': 100
        }, format='json')
        
        # Should not return 404
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_payment_verification_endpoint_exists(self):
        """Test that the payment verification endpoint exists"""
        url = '/api/payments/verify-payment/'
        response = self.client.post(url, {
            'reference': 'TEST_REF_123'
        }, format='json')
        
        # Should not return 404
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_simulation_mode_works(self):
        """Test that simulation mode works correctly"""
        # Create a mock payment
        payment = PaystackPayment.objects.create(
            user=self.user,
            email='test@example.com',
            amount=100,
            reference='SIM_TEST_123'
        )
        
        # Test verification in simulation mode
        paystack_service = PaystackService(simulation_mode=True)
        result = paystack_service.verify_transaction('SIM_TEST_123')
        
        self.assertTrue(result['success'])
        self.assertIn('SIMULATION', result['message'])
        
        # Check wallet was updated
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 100)
        
    def test_normal_mode_verification(self):
        """Test that normal mode still works (will fail without real Paystack)"""
        paystack_service = PaystackService(simulation_mode=False)
        result = paystack_service.verify_transaction('NONEXISTENT_REF')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)

class PaymentEndpointTestCase(TestCase):
    """Test payment endpoints are accessible"""
    
    def test_wallet_endpoints_respond(self):
        """Test that wallet endpoints respond (not 404)"""
        client = APIClient()
        
        # Test wallet endpoint
        response = client.get('/api/payments/wallet/')
        # May return 401 for auth, but not 404
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test wallet transactions endpoint  
        response = client.get('/api/payments/wallet/transactions/')
        # May return 401 for auth, but not 404
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test topup endpoint
        response = client.post('/api/payments/wallet/topup/', {}, format='json')
        # May return 401 for auth, but not 404
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
