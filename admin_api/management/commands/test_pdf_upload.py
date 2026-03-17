from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import SimpleUploadedFile
from books.models import Book, Author
import os

class Command(BaseCommand):
    help = 'Test PDF upload functionality'

    def handle(self, *args, **options):
        # Create a test author
        author, _ = Author.objects.get_or_create(
            name='Test Author',
            defaults={'bio': 'Author for testing PDF uploads'}
        )
        
        # Create a simple PDF file for testing
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Length 2 0 R\nstream\n>>\nxref\n0 65535 f\n<<\ntrailer\n<<\nstartxref\n%%EOF'
        
        # Create a test PDF file
        test_pdf = SimpleUploadedFile(
            "test_book.pdf",
            pdf_content,
            content_type="application/pdf"
        )
        
        # Create a book with the test PDF
        book = Book.objects.create(
            title='Test Book for PDF Upload',
            author=author,
            description='A test book to verify PDF upload functionality',
            isbn='1234567890',
            pages=100,
            language='en',
            pdf_file=test_pdf
        )
        
        self.stdout.write(self.style.SUCCESS(f'Created test book: {book.title}'))
        self.stdout.write(f'PDF file size: {book.file_size} bytes')
        self.stdout.write(f'PDF file URL: {book.pdf_file.url if book.pdf_file else "None"}')
        
        # Test file URL
        if book.pdf_file:
            self.stdout.write(f'PDF file path: {book.pdf_file.path}')
            self.stdout.write(f'PDF file exists: {os.path.exists(book.pdf_file.path)}')
        
        # Clean up
        book.delete()
        self.stdout.write(self.style.SUCCESS('Test completed successfully!'))
