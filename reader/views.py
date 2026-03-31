# reader/views.py  — book_pdf action uses FileResponse for proper streaming
import os
from django.http import FileResponse, HttpResponse, Http404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from books.models import Book
from library.models import UserLibrary, ReadingProgress, ReadingSession
from django.db import transaction
from django.contrib.auth import get_user_model
from payments.models import Wallet, Transaction
from reader.models import UnlockedPage, Note, Bookmark

User = get_user_model()


def get_user_from_jwt(request):
    if hasattr(request, 'user_payload') and request.user_payload:
        try:
            return User.objects.get(id=request.user_payload['user_id'])
        except (User.DoesNotExist, KeyError):
            return None
    return None


@api_view(['POST'])
@permission_classes([])
def unlock_page(request):
    """Unlock a specific page of a book"""
    book_id     = request.data.get('book_id')
    page_number = request.data.get('page_number')
    #user_id=request.data.get('user_id')
    print(f"just  DEBUG: Unlock request - user_id: {getattr(request, 'user_payload', {}).get('user_id')}, book_id: {book_id}, page_number: {page_number}")
    
    # TEMPORARILY DISABLE AUTH FOR TESTING
    # user = get_user_from_jwt(request)
    user = User.objects.get(id=3)  # Hardcoded user for testing
    
    if not book_id or page_number is None:
        return Response(
            {'error': 'book_id and page_number are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        book = Book.objects.get(id=book_id)
        print(f"just  DEBUG: Book found: {book.title}")
    except Book.DoesNotExist:
        print("just  DEBUG: Book not found")
        return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check if user has library entry (purchased or free access)
    library_entry = UserLibrary.objects.filter(user_id=user.id, book=book).first()
    print(f"just  DEBUG: Library entry: {library_entry}")
    
    # Allow page unlocking if:
    # 1. Book is free, OR
    # 2. User has purchased the book, OR  
    # 3. User is within 20% free preview range
    free_preview_pages = 1  # Always allow page 1
    if book.pages and book.pages > 0:
        free_preview_pages = max(1, int(book.pages * 0.2))  # 20% free preview
    
    if not book.is_free and not library_entry and page_number > free_preview_pages:
        print("just  DEBUG: No library entry and beyond free preview range")
        return Response(
            {'error': 'You must purchase this book first'},
            status=status.HTTP_403_FORBIDDEN,
        )
    
    if UnlockedPage.objects.filter(user_id=user.id, book=book, page_number=page_number).exists():
        print("just  DEBUG: Page already unlocked")
        return Response({'error': 'Page already unlocked'}, status=status.HTTP_400_BAD_REQUEST)

    wallet, _ = Wallet.objects.get_or_create(user_id=user.id)
    print(f"just  DEBUG: Wallet: {wallet.balance} coins")
    
    # Calculate per-page cost using same logic as serializers
    from decimal import Decimal
    if book.is_free or not book.price or book.price <= 0:
        page_cost = Decimal('0')
    elif book.pages and book.pages > 0:
        # Use same calculation as serializers with Decimal for consistency
        page_cost = Decimal(str(book.price)) / Decimal(str(book.pages))
        page_cost = page_cost.quantize(Decimal('0.0001'))  # Round to 4 decimal places
        # Ensure minimum cost of 1 coin per page
        page_cost = max(Decimal('1'), page_cost)
    else:
        page_cost = Decimal('10')  # Fallback for books without page count
    
    print(f"just  DEBUG: Calculated page cost: {page_cost} coins (Book price: {book.price} KES, Pages: {book.pages})")

    if wallet.balance < page_cost:
        return Response({'error': 'Insufficient balance'}, status=status.HTTP_402_PAYMENT_REQUIRED)

    with transaction.atomic():
        wallet.balance -= page_cost
        wallet.save()
        Transaction.objects.create(
            user_id=user.id,
            transaction_type='unlock_page',
            amount=-page_cost,
            description=f'Unlocked page {page_number} of {book.title}',
            status='completed'
        )
        UnlockedPage.objects.create(user_id=user.id, book=book, page_number=page_number)

    return Response({
        'message': 'Page unlocked successfully', 
        'remaining_balance': wallet.balance,
        'page_cost': page_cost,
        'book_price': float(book.price),
        'book_pages': book.pages,
        'per_page_cost': float(round(book.price / book.pages, 2)) if book.pages > 0 and book.price > 0 else 0
    })


@api_view(['GET'])
@permission_classes([])
def get_unlocked_pages(request, book_id):
    user = get_user_from_jwt(request)
    if not user:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

    pages = UnlockedPage.objects.filter(
        user_id=user.id, book=book
    ).values_list('page_number', flat=True)

    return Response({'unlocked_pages': list(pages)})


@api_view(['POST'])
@permission_classes([])
def create_note(request):
    """Create a new note for a page"""
    user = get_user_from_jwt(request)
    if not user:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    book_id = request.data.get('book_id')
    page_number = request.data.get('page_number')
    content = request.data.get('content')

    if not book_id or page_number is None or not content:
        return Response({'error': 'book_id, page_number, and content are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

    note = Note.objects.create(
        user_id=user.id,
        book=book,
        page_number=page_number,
        content=content
    )

    return Response({
        'id': note.id,
        'content': note.content,
        'page_number': note.page_number,
        'created_at': note.created_at
    })


@api_view(['GET'])
@permission_classes([])
def get_notes(request, book_id):
    """Get all notes for a book"""
    user = get_user_from_jwt(request)
    if not user:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

    notes = Note.objects.filter(user_id=user.id, book=book).order_by('created_at')
    return Response([{
        'id': note.id,
        'content': note.content,
        'page_number': note.page_number,
        'created_at': note.created_at
    } for note in notes])


@api_view(['DELETE'])
@permission_classes([])
def delete_note(request, note_id):
    """Delete a specific note"""
    user = get_user_from_jwt(request)
    if not user:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        note = Note.objects.get(id=note_id, user_id=user.id)
        note.delete()
        return Response({'message': 'Note deleted successfully'})
    except Note.DoesNotExist:
        return Response({'error': 'Note not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([])
def create_bookmark(request):
    """Create a new bookmark"""
    user = get_user_from_jwt(request)
    if not user:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    book_id = request.data.get('book_id')
    page_number = request.data.get('page_number')
    title = request.data.get('title', f'Page {page_number}')

    if not book_id or page_number is None:
        return Response({'error': 'book_id and page_number are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

    bookmark = Bookmark.objects.create(
        user_id=user.id,
        book=book,
        page_number=page_number,
        title=title
    )

    return Response({
        'id': bookmark.id,
        'title': bookmark.title,
        'page_number': bookmark.page_number,
        'created_at': bookmark.created_at
    })


@api_view(['GET'])
@permission_classes([])
def get_bookmarks(request, book_id):
    """Get all bookmarks for a book"""
    user = get_user_from_jwt(request)
    if not user:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

    bookmarks = Bookmark.objects.filter(user_id=user.id, book=book).order_by('page_number')
    return Response([{
        'id': bookmark.id,
        'title': bookmark.title,
        'page_number': bookmark.page_number,
        'created_at': bookmark.created_at
    } for bookmark in bookmarks])


@api_view(['DELETE'])
@permission_classes([])
def delete_bookmark(request, bookmark_id):
    """Delete a specific bookmark"""
    user = get_user_from_jwt(request)
    if not user:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        bookmark = Bookmark.objects.get(id=bookmark_id, user_id=user.id)
        bookmark.delete()
        return Response({'message': 'Bookmark deleted successfully'})
    except Bookmark.DoesNotExist:
        return Response({'error': 'Bookmark not found'}, status=status.HTTP_404_NOT_FOUND)


class ReaderViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def progress(self, request):
        user_id    = request.user_payload.get('user_id')
        book_id    = request.data.get('book_id')
        page       = request.data.get('page', 1)
        total_pages = request.data.get('total_pages')

        if not book_id:
            return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            book = Book.objects.prefetch_related('userlibrary_set').get(id=book_id)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        if not book.userlibrary_set.filter(user_id=user_id).exists():
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        progress, _ = ReadingProgress.objects.get_or_create(
            user_id=user_id, book=book,
            defaults={'current_page': page, 'total_pages': total_pages or book.pages},
        )
        progress.update_progress(page, total_pages or book.pages)

        return Response({
            'message': 'Progress updated',
            'progress': {
                'current_page':        progress.current_page,
                'total_pages':         progress.total_pages,
                'progress_percentage': progress.progress_percentage,
                'is_completed':        progress.is_completed,
            },
        })

    @action(detail=False, methods=['post'])
    def start_session(self, request):
        user_id    = request.user_payload.get('user_id')
        book_id    = request.data.get('book_id')
        start_page = request.data.get('start_page', 1)

        if not book_id:
            return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            book = Book.objects.prefetch_related('userlibrary_set').get(id=book_id)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        if not book.userlibrary_set.filter(user_id=user_id).exists():
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        session = ReadingSession.objects.create(
            user_id=user_id, book=book,
            start_page=start_page, start_time=timezone.now(),
        )
        return Response({'session_id': session.id, 'message': 'Session started'},
                        status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def end_session(self, request):
        user_id    = request.user_payload.get('user_id')
        session_id = request.data.get('session_id')
        end_page   = request.data.get('end_page')

        if not session_id:
            return Response({'error': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = ReadingSession.objects.get(id=session_id, user_id=user_id)
        except ReadingSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        session.end_session(end_page)
        return Response({'message': 'Session ended', 'duration_minutes': session.duration_minutes})

    @action(detail=False, methods=['get'])
    def book_pdf(self, request):
        """
        Serve the PDF using FileResponse which:
        - streams the file in chunks instead of reading it all into memory
        - sets Content-Length correctly from the filesystem
        - supports Range requests (partial content / resume) automatically
          when used with Django's development server or nginx X-Accel-Redirect
        """
        user_id = request.user_payload.get('user_id')
        book_id = request.GET.get('book_id')

        if not book_id:
            return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            book = Book.objects.prefetch_related('userlibrary_set').get(id=book_id)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        if not book.userlibrary_set.filter(user_id=user_id).exists():
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        if not book.pdf_file:
            return Response({'error': 'PDF not available'}, status=status.HTTP_404_NOT_FOUND)

        # FileResponse opens the file itself, streams it in chunks, and
        # sets Content-Length from os.path.getsize — no manual file_size field needed
        response = FileResponse(
            book.pdf_file.open('rb'),
            content_type='application/pdf',
            as_attachment=False,          # inline display, not download
            filename=f'{book.title}.pdf',
        )
        response['Accept-Ranges'] = 'bytes'  # signals range-request support to the browser
        return response