from django.core.management.base import BaseCommand
from django.utils import timezone
from .models import PaymentPlan


class Command(BaseCommand):
    help = 'Create default payment plans'

    def handle(self, *args, **options):
        # Create default payment plans
        plans_data = [
            {
                'name': 'Basic Plan',
                'description': 'Access to 5 books for 30 days',
                'price': 9.99,
                'duration_days': 30,
                'max_books': 5,
                'features': ['Access to 5 books', '30 days access', 'Basic support']
            },
            {
                'name': 'Standard Plan',
                'description': 'Access to 15 books for 60 days',
                'price': 19.99,
                'duration_days': 60,
                'max_books': 15,
                'features': ['Access to 15 books', '60 days access', 'Priority support', 'Download for offline reading']
            },
            {
                'name': 'Premium Plan',
                'description': 'Unlimited access to all books for 90 days',
                'price': 39.99,
                'duration_days': 90,
                'max_books': 999,  # Effectively unlimited
                'features': ['Unlimited book access', '90 days access', 'Premium support', 'Download for offline reading', 'Early access to new books']
            },
            {
                'name': 'Annual Plan',
                'description': 'Unlimited access to all books for 365 days',
                'price': 99.99,
                'duration_days': 365,
                'max_books': 999,  # Effectively unlimited
                'features': ['Unlimited book access', '365 days access', 'Premium support', 'Download for offline reading', 'Early access to new books', 'Exclusive content']
            }
        ]

        created_count = 0
        for plan_data in plans_data:
            plan, created = PaymentPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created payment plan: {plan.name}'))
                created_count += 1
            else:
                self.stdout.write(self.style.WARNING(f'Payment plan already exists: {plan.name}'))

        self.stdout.write(self.style.SUCCESS(f'Setup complete. Created {created_count} new payment plans.'))
