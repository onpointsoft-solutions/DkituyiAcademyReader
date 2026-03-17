from django.core.management.base import BaseCommand
from books.models import Book, Author, Category
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **options):
        # Create sample categories
        categories_data = [
            'Fiction', 'Non-Fiction', 'Science', 'Technology', 'Business', 
            'Self-Help', 'Biography', 'History', 'Programming', 'Design'
        ]
        
        for cat_name in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'Books in {cat_name} category'}
            )
            if created:
                self.stdout.write(f'Created category: {cat_name}')

        # Create sample authors
        authors_data = [
            {'name': 'John Doe', 'bio': 'Fiction writer and novelist'},
            {'name': 'Jane Smith', 'bio': 'Technology expert and author'},
            {'name': 'Robert Johnson', 'bio': 'Business consultant and writer'},
            {'name': 'Emily Brown', 'bio': 'Self-help and personal development author'},
            {'name': 'Michael Wilson', 'bio': 'Science educator and researcher'},
        ]
        
        for author_data in authors_data:
            author, created = Author.objects.get_or_create(
                name=author_data['name'],
                defaults={'bio': author_data['bio']}
            )
            if created:
                self.stdout.write(f'Created author: {author_data["name"]}')

        # Create sample books
        books_data = [
            {
                'title': 'The Art of Programming',
                'subtitle': 'A Comprehensive Guide',
                'author_name': 'Jane Smith',
                'categories': ['Technology', 'Programming'],
                'pages': 450,
                'language': 'en',
                'description': 'A comprehensive guide to modern programming techniques and best practices.'
            },
            {
                'title': 'Business Success Secrets',
                'subtitle': 'Strategies for Growth',
                'author_name': 'Robert Johnson',
                'categories': ['Business', 'Self-Help'],
                'pages': 320,
                'language': 'en',
                'description': 'Learn the secrets to building a successful business in the modern economy.'
            },
            {
                'title': 'The Science of Everything',
                'subtitle': 'Understanding Our World',
                'author_name': 'Michael Wilson',
                'categories': ['Science', 'Non-Fiction'],
                'pages': 580,
                'language': 'en',
                'description': 'An accessible guide to understanding the scientific principles that govern our world.'
            },
            {
                'title': 'Design Thinking',
                'subtitle': 'Creative Problem Solving',
                'author_name': 'Emily Brown',
                'categories': ['Design', 'Business'],
                'pages': 280,
                'language': 'en',
                'description': 'Learn how to apply design thinking principles to solve complex problems.'
            },
            {
                'title': 'The Great Adventure',
                'subtitle': 'A Journey of Discovery',
                'author_name': 'John Doe',
                'categories': ['Fiction'],
                'pages': 400,
                'language': 'en',
                'description': 'An epic tale of adventure and self-discovery in a mysterious land.'
            },
        ]
        
        for book_data in books_data:
            author = Author.objects.get(name=book_data['author_name'])
            
            book, created = Book.objects.get_or_create(
                title=book_data['title'],
                defaults={
                    'subtitle': book_data['subtitle'],
                    'author': author,
                    'description': book_data['description'],
                    'pages': book_data['pages'],
                    'language': book_data['language'],
                }
            )
            
            if created:
                # Add categories
                for cat_name in book_data['categories']:
                    category = Category.objects.get(name=cat_name)
                    book.categories.add(category)
                
                self.stdout.write(f'Created book: {book_data["title"]}')

        self.stdout.write(
            self.style.SUCCESS('Sample data created successfully!')
        )
