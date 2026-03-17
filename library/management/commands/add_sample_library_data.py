from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from books.models import Book, Author
from library.models import UserLibrary, ReadingProgress


class Command(BaseCommand):
    help = 'Add sample library data for testing'

    def handle(self, *args, **options):
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created test user: {user.username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Test user already exists: {user.username}'))
        
        # Get existing books or create sample books
        books = Book.objects.all()[:5]  # Get first 5 books
        
        if not books.exists():
            self.stdout.write(self.style.WARNING('No books found. Creating sample books...'))
            
            # Create sample author
            author, _ = Author.objects.get_or_create(
                name='Sample Author',
                defaults={'bio': 'A sample author for testing'}
            )
            
            # Create sample books
            sample_books = [
                {
                    'title': 'The Great Adventure',
                    'author': author,
                    'isbn': '1234567890',
                    'pages': 250,
                    'description': 'A thrilling adventure story.',
                    'cover_url': 'https://via.placeholder.com/200x280?text=Great+Adventure'
                },
                {
                    'title': 'Mystery of the Lost City',
                    'author': author,
                    'isbn': '0987654321',
                    'pages': 320,
                    'description': 'An exciting mystery novel.',
                    'cover_url': 'https://via.placeholder.com/200x280?text=Mystery+City'
                },
                {
                    'title': 'Science Fiction Tales',
                    'author': author,
                    'isbn': '1122334455',
                    'pages': 180,
                    'description': 'A collection of sci-fi stories.',
                    'cover_url': 'https://via.placeholder.com/200x280?text=Sci-Fi+Tales'
                }
            ]
            
            for book_data in sample_books:
                book = Book.objects.create(**book_data)
                books.append(book)
                self.stdout.write(self.style.SUCCESS(f'Created book: {book.title}'))
        else:
            books = list(books)
            self.stdout.write(self.style.SUCCESS(f'Found {len(books)} existing books'))
        
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
                self.stdout.write(self.style.SUCCESS(f'Added "{book.title}" to user library'))
            else:
                self.stdout.write(self.style.WARNING(f'"{book.title}" already in user library'))
            
            # Add reading progress for some books
            if i < 3:  # Add progress for first 3 books
                progress_percentages = [25, 60, 100]  # Different progress levels
                progress = progress_percentages[i]
                
                progress_entry, created = ReadingProgress.objects.get_or_create(
                    user_id=user.id,
                    book=book,
                    defaults={
                        'current_page': int(book.pages * progress / 100),
                        'total_pages': book.pages,
                        'progress_percentage': progress,
                        'is_completed': progress >= 100,
                        'reading_time_minutes': progress * 2  # 2 minutes per percent
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Added {progress}% progress for "{book.title}"'))
                else:
                    self.stdout.write(self.style.WARNING(f'Progress already exists for "{book.title}"'))
        
        self.stdout.write(self.style.SUCCESS('Sample library data added successfully!'))
        self.stdout.write(f'User: {user.username} (ID: {user.id})')
        self.stdout.write(f'Library books: {UserLibrary.objects.filter(user_id=user.id).count()}')
        self.stdout.write(f'Progress entries: {ReadingProgress.objects.filter(user_id=user.id).count()}')
