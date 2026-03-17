from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.email import EmailService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send welcome emails to existing users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Send welcome email to specific user ID only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        dry_run = options.get('dry_run', False)
        
        if user_id:
            users = User.objects.filter(id=user_id)
        else:
            users = User.objects.all()
        
        self.stdout.write(f"Found {users.count()} users to process")
        
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                if dry_run:
                    self.stdout.write(f"[DRY RUN] Would send welcome email to: {user.email} ({user.get_full_name() or user.username})")
                    success_count += 1
                else:
                    success = EmailService.send_welcome_email(
                        user_email=user.email,
                        user_name=user.get_full_name() or user.username,
                        user_id=user.id
                    )
                    
                    if success:
                        self.stdout.write(self.style.SUCCESS(f"✅ Welcome email sent to: {user.email}"))
                        success_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f"❌ Failed to send welcome email to: {user.email}"))
                        error_count += 1
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error processing user {user.email}: {str(e)}"))
                error_count += 1
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would have sent {success_count} welcome emails"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Welcome email campaign completed: {success_count} sent, {error_count} failed"))
