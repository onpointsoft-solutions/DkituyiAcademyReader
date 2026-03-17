from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from books.models import Book
from library.models import UserLibrary, ReadingProgress


class Command(BaseCommand):
    help = 'Add library data for existing users'

    def handle(self, *args, **options):
        # Get existing users
        users = User.objects.all()
        
        if not users.exists():
            self.stdout.write(self.style.WARNING('No users found. Please create users first.'))
            return
        
        # Get existing books
        books = Book.objects.all()[:5]  # Get first 5 books
        
        if not books.exists():
            self.stdout.write(self.style.WARNING('No books found. Please create books first.'))
            return
        
        books = list(books)
        self.stdout.write(self.style.SUCCESS(f'Found {len(users)} users and {len(books)} books'))
        
        for user in users:
            self.stdout.write(f'\nProcessing user: {user.username} (ID: {user.id})')
            
            # Add books to user library
            for i, book in enumerate(books):
                library_entry, created = UserLibrary.objects.get_or_create(
                    user_id=user.id,
                    book=book,
                    defaults={
                        'purchase_date': timezone.now(),
                        'is_active': True
                    }
                )
                
                if created:
                    self.stdout.write(f'  ✓ Added "{book.title}" to library')
                else:
                    self.stdout.write(f'  - "{book.title}" already in library')
                
                # Add reading progress for some books
                if i < 3:  # Add progress for first 3 books
                    progress_percentages = [25, 60, 100]  # Different progress levels
                    progress = progress_percentages[i]
                    
                    progress_entry, created = ReadingProgress.objects.get_or_create(
                        user_id=user.id,
                        book=book,
                        defaults={
                            'current_page': int(book.pages * progress / 100) if book.pages else 10,
                            'total_pages': book.pages or 40,
                            'progress_percentage': progress,
                            'is_completed': progress >= 100,
                            'reading_time_minutes': progress * 2  # 2 minutes per percent
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'  ✓ Added {progress}% progress for "{book.title}"')
                    else:
                        self.stdout.write(f'  - Progress already exists for "{book.title}"')
        
        self.stdout.write(self.style.SUCCESS('\nLibrary data added for all users successfully!'))
        
        # Summary
        total_library_entries = UserLibrary.objects.count()
        total_progress_entries = ReadingProgress.objects.count()
        
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'  Total library entries: {total_library_entries}')
        self.stdout.write(f'  Total progress entries: {total_progress_entries}')
        self.stdout.write(f'  Users with library data: {UserLibrary.objects.values("user_id").distinct().count()}')
