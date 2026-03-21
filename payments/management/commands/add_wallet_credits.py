from django.core.management.base import BaseCommand
from payments.models import Wallet, Transaction
from django.utils import timezone
from decimal import Decimal

class Command(BaseCommand):
    help = 'Add credits to user wallet for testing'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, required=True, help='User ID to add credits to')
        parser.add_argument('--amount', type=float, required=True, help='Amount to add')
        parser.add_argument('--description', type=str, default='Manual credit addition', help='Transaction description')

    def handle(self, *args, **options):
        user_id = options['user_id']
        amount = Decimal(str(options['amount']))  # Convert float to Decimal
        description = options['description']

        try:
            # Get or create wallet
            wallet, created = Wallet.objects.get_or_create(
                user_id=user_id,
                defaults={'balance': Decimal('0.00')}
            )

            if created:
                self.stdout.write(f'Created new wallet for user {user_id}')

            # Add funds to wallet
            old_balance = wallet.balance
            wallet.add_funds(amount)
            new_balance = wallet.balance

            # Create transaction record
            transaction = Transaction.objects.create(
                user_id=user_id,
                amount=amount,
                transaction_type='topup',
                status='completed',
                paystack_reference=f'ADMIN_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                description=description
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully added KES {amount} to user {user_id} wallet.\n'
                    f'Previous balance: KES {old_balance}\n'
                    f'New balance: KES {new_balance}\n'
                    f'Transaction ID: {transaction.id}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error adding credits: {str(e)}')
            )
