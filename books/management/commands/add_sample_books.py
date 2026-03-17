from django.core.management.base import BaseCommand
from books.models import Book, Author
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Add sample African books to the database'

    def handle(self, *args, **options):
        # Create or get sample authors
        authors_data = [
            {'name': 'Chinua Achebe', 'bio': 'Nigerian novelist, poet, professor, and critic.'},
            {'name': 'Nadine Gordimer', 'bio': 'South African writer, political activist and Nobel laureate.'},
            {'name': 'Ngũgĩ wa Thiong\'o', 'bio': 'Kenyan writer and academic who writes primarily in Gikuyu and English.'},
            {'name': 'Chimamanda Ngozi Adichie', 'bio': 'Nigerian writer whose works range from novels to short stories to nonfiction.'},
            {'name': 'Wole Soyinka', 'bio': 'Nigerian playwright, novelist, poet, and essayist in the English language.'},
        ]

        authors = {}
        for author_data in authors_data:
            author, created = Author.objects.get_or_create(
                name=author_data['name'],
                defaults={'bio': author_data['bio']}
            )
            authors[author_data['name']] = author
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Created author: {author.name}"))

        # Sample African books
        books_data = [
            {
                'title': 'Things Fall Apart',
                'author': 'Chinua Achebe',
                'description': 'A novel about Nigerian village life and the arrival of European colonialism.',
                'isbn': '978-0-435-90545-5',
                'publication_date': '1958-01-01',
                'language': 'en',
                'pages': 209,
                'cover_url': 'https://via.placeholder.com/400x600/2c3e50/ffffff?text=Things+Fall+Apart',
                'rating': 4.5,
            },
            {
                'title': 'Half of a Yellow Sun',
                'author': 'Chimamanda Ngozi Adichie',
                'description': 'A novel set before and during the Nigerian Civil War.',
                'isbn': '978-0-307-27873-0',
                'publication_date': '2006-01-01',
                'language': 'en',
                'pages': 433,
                'cover_url': 'https://via.placeholder.com/400x600/e74c3c/ffffff?text=Half+of+a+Yellow+Sun',
                'rating': 4.7,
            },
            {
                'title': 'A Grain of Wheat',
                'author': 'Ngũgĩ wa Thiong\'o',
                'description': 'A novel about Kenya\'s struggle for independence and its aftermath.',
                'isbn': '978-0-14-303690-3',
                'publication_date': '1967-01-01',
                'language': 'en',
                'pages': 280,
                'cover_url': 'https://via.placeholder.com/400x600/27ae60/ffffff?text=A+Grain+of+Wheat',
                'rating': 4.3,
            },
            {
                'title': "July's People",
                'author': 'Nadine Gordimer',
                'description': 'A novel set in a future South Africa during a fictional civil war.',
                'isbn': '978-0-14-006140-1',
                'publication_date': '1981-01-01',
                'language': 'en',
                'pages': 160,
                'cover_url': 'https://via.placeholder.com/400x600/8e44ad/ffffff?text=July%27s+People',
                'rating': 4.1,
            },
            {
                'title': 'The Man Died: Prison Notes',
                'author': 'Wole Soyinka',
                'description': 'A collection of notes written during Soyinka\'s imprisonment.',
                'isbn': '978-0-435-08987-1',
                'publication_date': '1972-01-01',
                'language': 'en',
                'pages': 238,
                'cover_url': 'https://via.placeholder.com/400x600/f39c12/ffffff?text=The+Man+Died',
                'rating': 4.4,
            },
        ]

        books_added = 0
        for book_data in books_data:
            author = authors[book_data['author']]
            
            book, created = Book.objects.get_or_create(
                title=book_data['title'],
                author=author,
                defaults={
                    'description': book_data['description'],
                    'isbn': book_data['isbn'],
                    'publication_date': book_data['publication_date'],
                    'language': book_data['language'],
                    'pages': book_data['pages'],
                    'cover_url': book_data['cover_url'],
                    'rating': book_data['rating'],
                }
            )
            
            if created:
                books_added += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created book: {book.title} by {book.author.name}"))
            else:
                self.stdout.write(f"📚 Book already exists: {book.title}")

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Added {books_added} new African books to the database!"))
        self.stdout.write(self.style.SUCCESS(f"📚 Total books in database: {Book.objects.count()}"))
