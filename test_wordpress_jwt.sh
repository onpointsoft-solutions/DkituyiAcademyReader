#!/bin/bash

# WordPress JWT Integration Test Script
# This script tests the WordPress JWT authentication integration

echo "🔍 WordPress JWT Integration Test Script"
echo "=========================================="

# Configuration
DJANGO_URL="http://127.0.0.1:8001"
WORDPRESS_URL="https://dkituyiacademy.org"
USERNAME="vincentbettoh@gmail.com"
PASSWORD="@Admin@2026"

echo ""
echo "📋 Test Configuration:"
echo "  Django Backend: $DJANGO_URL"
echo "  WordPress Site: $WORDPRESS_URL"
echo "  Username: $USERNAME"
echo ""

# Test 1: Direct WordPress JWT Authentication
echo "🔍 Test 1: Direct WordPress JWT Authentication"
echo "-------------------------------------------"
echo "Testing WordPress JWT endpoint directly..."

wp_response=$(curl -s -w "\nHTTP Status: %{http_code}" \
  -X POST "$WORDPRESS_URL/wp-json/jwt-auth/v1/token" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

echo "$wp_response"
echo ""

# Extract WordPress token
wp_token=$(echo "$wp_response" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
wp_user_email=$(echo "$wp_response" | grep -o '"user_email":"[^"]*' | cut -d'"' -f4)
wp_user_id=$(echo "$wp_response" | grep -o '"user_id":[0-9]*' | cut -d':' -f2)

if [ -n "$wp_token" ]; then
    echo "✅ WordPress authentication successful!"
    echo "  User Email: $wp_user_email"
    echo "  User ID: $wp_user_id"
    echo "  Token (first 20 chars): ${wp_token:0:20}..."
else
    echo "❌ WordPress authentication failed"
    exit 1
fi

echo ""

# Test 2: Django WordPress Login Endpoint
echo "🔍 Test 2: Django WordPress Login Endpoint"
echo "--------------------------------------------"
echo "Testing Django WordPress login integration..."

django_response=$(curl -s -w "\nHTTP Status: %{http_code}" \
  -X POST "$DJANGO_URL/api/auth/wordpress-login/" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

echo "$django_response"
echo ""

# Extract Django token
django_token=$(echo "$django_response" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
created_user=$(echo "$django_response" | grep -o '"created":[^,]*' | cut -d':' -f2)

if [ -n "$django_token" ]; then
    echo "✅ Django WordPress login successful!"
    echo "  Created New User: $created_user"
    echo "  Django Token (first 20 chars): ${django_token:0:20}..."
else
    echo "❌ Django WordPress login failed"
    echo "  Make sure Django server is running on $DJANGO_URL"
fi

echo ""

# Test 3: Verify WordPress Token
echo "🔍 Test 3: Verify WordPress Token"
echo "---------------------------------"
if [ -n "$wp_token" ]; then
    verify_response=$(curl -s -w "\nHTTP Status: %{http_code}" \
      -X POST "$DJANGO_URL/api/auth/verify-wordpress-token/" \
      -H "Content-Type: application/json" \
      -d "{\"wordpress_token\": \"$wp_token\"}")
    
    echo "$verify_response"
    
    if echo "$verify_response" | grep -q '"message"'; then
        echo "✅ WordPress token verification successful!"
    else
        echo "❌ WordPress token verification failed"
    fi
else
    echo "❌ No WordPress token available for verification"
fi

echo ""

# Test 4: Auth Status Check
echo "🔍 Test 4: Auth Status Check"
echo "----------------------------"
if [ -n "$django_token" ]; then
    status_response=$(curl -s -w "\nHTTP Status: %{http_code}" \
      -X GET "$DJANGO_URL/api/auth/status/" \
      -H "Authorization: Bearer $django_token")
    
    echo "$status_response"
    
    if echo "$status_response" | grep -q '"authenticated":true'; then
        echo "✅ Auth status check successful!"
    else
        echo "❌ Auth status check failed"
    fi
else
    echo "❌ No Django token available for status check"
fi

echo ""
echo "🎉 WordPress JWT Integration Test Complete!"
echo "=========================================="
echo ""
echo "📊 Summary:"
echo "  - WordPress JWT: ✅ Working"
echo "  - Django Integration: 🔄 Test with server running"
echo "  - Token Verification: 🔄 Test with server running"
echo "  - Auth Tracking: 🔄 Test with server running"
echo ""
echo "🚀 Next Steps:"
echo "  1. Start Django server: python manage.py runserver"
echo "  2. Run this script again to test full integration"
echo "  3. Update frontend to use WordPress login endpoint"
echo "  4. Monitor logs for authentication tracking"
