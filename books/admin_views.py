from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Book, Author, Category, BookChapter, BookPage
from .forms import BookForm, ChapterForm, PageForm


@staff_member_required
def admin_dashboard(request):
    """Admin dashboard for book management"""
    books = Book.objects.all().order_by('-created_at')
    authors = Author.objects.all().order_by('name')
    categories = Category.objects.all().order_by('name')
    
    context = {
        'books': books,
        'authors': authors,
        'categories': categories,
        'title': 'Book Reader Admin Dashboard'
    }
    return render(request, 'admin/books/dashboard.html', context)


@staff_member_required
def add_book_manual(request):
    """Add a new book with manual content entry"""
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.content_source = 'manual'
            book.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, f'Book "{book.title}" created successfully!')
            return redirect('admin_book_chapters', book_id=book.id)
    else:
        form = BookForm()
    
    context = {
        'form': form,
        'title': 'Add New Book (Manual Content)',
        'action': 'Create'
    }
    return render(request, 'admin/books/book_form.html', context)


@staff_member_required
def edit_book(request, book_id):
    """Edit an existing book"""
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f'Book "{book.title}" updated successfully!')
            return redirect('admin_dashboard')
    else:
        form = BookForm(instance=book)
    
    context = {
        'form': form,
        'book': book,
        'title': f'Edit Book: {book.title}',
        'action': 'Update'
    }
    return render(request, 'admin/books/book_form.html', context)


@staff_member_required
def manage_chapters(request, book_id):
    """Manage chapters for a book"""
    book = get_object_or_404(Book, id=book_id)
    chapters = book.chapters.all().order_by('chapter_number')
    
    context = {
        'book': book,
        'chapters': chapters,
        'title': f'Manage Chapters: {book.title}'
    }
    return render(request, 'admin/books/chapters.html', context)


@staff_member_required
def add_chapter(request, book_id):
    """Add a new chapter to a book"""
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        form = ChapterForm(request.POST)
        if form.is_valid():
            chapter = form.save(commit=False)
            chapter.book = book
            chapter.save()
            
            messages.success(request, f'Chapter "{chapter.title}" added successfully!')
            return redirect('admin_book_chapters', book_id=book.id)
    else:
        # Set default chapter number
        last_chapter = book.chapters.all().order_by('-chapter_number').first()
        default_number = (last_chapter.chapter_number + 1) if last_chapter else 1
        form = ChapterForm(initial={'chapter_number': default_number})
    
    context = {
        'form': form,
        'book': book,
        'title': f'Add Chapter to: {book.title}',
        'action': 'Create'
    }
    return render(request, 'admin/books/chapter_form.html', context)


@staff_member_required
def edit_chapter(request, book_id, chapter_id):
    """Edit an existing chapter"""
    book = get_object_or_404(Book, id=book_id)
    chapter = get_object_or_404(BookChapter, id=chapter_id, book=book)
    
    if request.method == 'POST':
        form = ChapterForm(request.POST, instance=chapter)
        if form.is_valid():
            form.save()
            messages.success(request, f'Chapter "{chapter.title}" updated successfully!')
            return redirect('admin_book_chapters', book_id=book.id)
    else:
        form = ChapterForm(instance=chapter)
    
    context = {
        'form': form,
        'book': book,
        'chapter': chapter,
        'title': f'Edit Chapter: {chapter.title}',
        'action': 'Update'
    }
    return render(request, 'admin/books/chapter_form.html', context)


@staff_member_required
def manage_pages(request, book_id, chapter_id):
    """Manage pages for a chapter"""
    book = get_object_or_404(Book, id=book_id)
    chapter = get_object_or_404(BookChapter, id=chapter_id, book=book)
    pages = chapter.pages.all().order_by('page_number')
    
    context = {
        'book': book,
        'chapter': chapter,
        'pages': pages,
        'title': f'Manage Pages: {chapter.title}'
    }
    return render(request, 'admin/books/pages.html', context)


@staff_member_required
def add_page(request, book_id, chapter_id):
    """Add a new page to a chapter"""
    book = get_object_or_404(Book, id=book_id)
    chapter = get_object_or_404(BookChapter, id=chapter_id, book=book)
    
    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)
            page.chapter = chapter
            page.save()
            
            messages.success(request, f'Page {page.page_number} added successfully!')
            return redirect('admin_chapter_pages', book_id=book.id, chapter_id=chapter.id)
    else:
        # Set default page number
        last_page = chapter.pages.all().order_by('-page_number').first()
        default_number = (last_page.page_number + 1) if last_page else 1
        form = PageForm(initial={'page_number': default_number})
    
    context = {
        'form': form,
        'book': book,
        'chapter': chapter,
        'title': f'Add Page to: {chapter.title}',
        'action': 'Create'
    }
    return render(request, 'admin/books/page_form.html', context)


@staff_member_required
def edit_page(request, book_id, chapter_id, page_id):
    """Edit an existing page"""
    book = get_object_or_404(Book, id=book_id)
    chapter = get_object_or_404(BookChapter, id=chapter_id, book=book)
    page = get_object_or_404(BookPage, id=page_id, chapter=chapter)
    
    if request.method == 'POST':
        form = PageForm(request.POST, instance=page)
        if form.is_valid():
            form.save()
            messages.success(request, f'Page {page.page_number} updated successfully!')
            return redirect('admin_chapter_pages', book_id=book.id, chapter_id=chapter.id)
    else:
        form = PageForm(instance=page)
    
    context = {
        'form': form,
        'book': book,
        'chapter': chapter,
        'page': page,
        'title': f'Edit Page {page.page_number}',
        'action': 'Update'
    }
    return render(request, 'admin/books/page_form.html', context)


@staff_member_required
@require_POST
def delete_chapter(request, book_id, chapter_id):
    """Delete a chapter"""
    book = get_object_or_404(Book, id=book_id)
    chapter = get_object_or_404(BookChapter, id=chapter_id, book=book)
    
    chapter.delete()
    messages.success(request, f'Chapter "{chapter.title}" deleted successfully!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('admin_book_chapters', book_id=book.id)


@staff_member_required
@require_POST
def delete_page(request, book_id, chapter_id, page_id):
    """Delete a page"""
    book = get_object_or_404(Book, id=book_id)
    chapter = get_object_or_404(BookChapter, id=chapter_id, book=book)
    page = get_object_or_404(BookPage, id=page_id, chapter=chapter)
    
    page.delete()
    messages.success(request, f'Page {page.page_number} deleted successfully!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('admin_chapter_pages', book_id=book.id, chapter_id=chapter.id)


@staff_member_required
def book_stats(request):
    """View book statistics"""
    books = Book.objects.all()
    total_books = books.count()
    free_books = books.filter(is_free=True).count()
    paid_books = books.filter(is_free=False).count()
    
    # Content source stats
    pdf_books = books.filter(content_source='pdf').count()
    manual_books = books.filter(content_source='manual').count()
    
    # Chapter and page stats
    total_chapters = BookChapter.objects.count()
    total_pages = BookPage.objects.count()
    
    context = {
        'total_books': total_books,
        'free_books': free_books,
        'paid_books': paid_books,
        'pdf_books': pdf_books,
        'manual_books': manual_books,
        'total_chapters': total_chapters,
        'total_pages': total_pages,
        'title': 'Book Statistics'
    }
    return render(request, 'admin/books/stats.html', context)
