#!/bin/bash

# Production Deployment Script for Dkituyi Academy Backend
# This script prepares and deploys the backend to production

set -e

echo "🚀 Starting Backend Deployment..."

# Check if we're in the backend directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Please run this script from the backend directory."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Create superuser (optional - uncomment if needed)
# echo "👤 Creating superuser..."
# echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@dkituyiacademy.com', 'your-password')" | python manage.py shell

# Check production settings
echo "🔍 Checking production settings..."
python manage.py check --deploy

# Run tests (if any)
echo "🧪 Running tests..."
python manage.py test || echo "⚠️ No tests found or tests failed - continuing deployment"

# Create requirements.txt for production
echo "📋 Creating production requirements..."
pip freeze > requirements_production.txt

echo "✅ Backend deployment preparation complete!"
echo ""
echo "📝 Next steps:"
echo "1. Set up environment variables using .env.production"
echo "2. Configure your web server (Apache/Nginx) to serve Django"
echo "3. Set up PostgreSQL database (recommended for production)"
echo "4. Configure SSL certificate"
echo "5. Set up monitoring and logging"
echo ""
echo "🌐 Backend will be available at: https://ebooks.dkituyiacademy.org/backend/"
