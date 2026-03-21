from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from books.models import Book
from library.models import UserLibrary
from .models import Bookmark, Highlight, Note, ReadingSession, ScreenshotWarning
import json
from datetime import timedelta

class ReadingFeaturesViewSet(viewsets.GenericViewSet):
    """
    ViewSet for reading features: bookmarks, highlights, notes, and screenshot protection
    """
    permission_classes = [IsAuthenticated]
    
    def get_user_id(self):
        """Get user ID from JWT token"""
        return self.request.user_payload.get('user_id')
    
    def verify_book_access(self, book_id):
        """Verify user has access to the book"""
        user_id = self.get_user_id()
        try:
            book = Book.objects.get(id=book_id)
            if not UserLibrary.objects.filter(user_id=user_id, book=book, is_active=True).exists():
                return None, Response(
                    {'error': 'Access denied to this book'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            return book, None
        except Book.DoesNotExist:
            return None, Response(
                {'error': 'Book not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Bookmark Features
    @action(detail=False, methods=['post'])
    def add_bookmark(self, request):
        """Add a bookmark to a specific page"""
        user_id = self.get_user_id()
        book_id = request.data.get('book_id')
        page_number = request.data.get('page_number')
        position = request.data.get('position', {})
        title = request.data.get('title', '')
        note = request.data.get('note', '')
        
        book, error_response = self.verify_book_access(book_id)
        if error_response:
            return error_response
        
        bookmark, created = Bookmark.objects.get_or_create(
            user_id=user_id,
            book=book,
            page_number=page_number,
            position=position,
            defaults={
                'title': title or f"Page {page_number}",
                'note': note
            }
        )
        
        if not created:
            # Update existing bookmark
            bookmark.title = title or f"Page {page_number}"
            bookmark.note = note
            bookmark.save()
        
        return Response({
            'message': 'Bookmark saved successfully',
            'bookmark': {
                'id': bookmark.id,
                'page_number': bookmark.page_number,
                'position': bookmark.position,
                'title': bookmark.title,
                'note': bookmark.note,
                'created_at': bookmark.created_at
            }
        })
    
    @action(detail=False, methods=['get'])
    def get_bookmarks(self, request):
        """Get all bookmarks for a book"""
        user_id = self.get_user_id()
        book_id = request.GET.get('book_id')
        
        book, error_response = self.verify_book_access(book_id)
        if error_response:
            return error_response
        
        bookmarks = Bookmark.objects.filter(user_id=user_id, book=book).order_by('page_number')
        
        return Response({
            'bookmarks': [
                {
                    'id': bookmark.id,
                    'page_number': bookmark.page_number,
                    'position': bookmark.position,
                    'title': bookmark.title,
                    'note': bookmark.note,
                    'created_at': bookmark.created_at
                }
                for bookmark in bookmarks
            ]
        })
    
    @action(detail=False, methods=['delete'])
    def delete_bookmark(self, request):
        """Delete a bookmark"""
        user_id = self.get_user_id()
        bookmark_id = request.data.get('bookmark_id')
        
        try:
            bookmark = Bookmark.objects.get(id=bookmark_id, user_id=user_id)
            bookmark.delete()
            return Response({'message': 'Bookmark deleted successfully'})
        except Bookmark.DoesNotExist:
            return Response(
                {'error': 'Bookmark not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Highlight Features
    @action(detail=False, methods=['post'])
    def add_highlight(self, request):
        """Add a highlight to text"""
        user_id = self.get_user_id()
        book_id = request.data.get('book_id')
        page_number = request.data.get('page_number')
        start_position = request.data.get('start_position', {})
        end_position = request.data.get('end_position', {})
        selected_text = request.data.get('selected_text', '')
        color = request.data.get('color', '#ffff00')
        note = request.data.get('note', '')
        
        book, error_response = self.verify_book_access(book_id)
        if error_response:
            return error_response
        
        highlight = Highlight.objects.create(
            user_id=user_id,
            book=book,
            page_number=page_number,
            start_position=start_position,
            end_position=end_position,
            selected_text=selected_text,
            color=color,
            note=note
        )
        
        return Response({
            'message': 'Highlight added successfully',
            'highlight': {
                'id': highlight.id,
                'page_number': highlight.page_number,
                'start_position': highlight.start_position,
                'end_position': highlight.end_position,
                'selected_text': highlight.selected_text,
                'color': highlight.color,
                'note': highlight.note,
                'created_at': highlight.created_at
            }
        })
    
    @action(detail=False, methods=['get'])
    def get_highlights(self, request):
        """Get all highlights for a book"""
        user_id = self.get_user_id()
        book_id = request.GET.get('book_id')
        page_number = request.GET.get('page_number')
        
        book, error_response = self.verify_book_access(book_id)
        if error_response:
            return error_response
        
        highlights = Highlight.objects.filter(user_id=user_id, book=book)
        if page_number:
            highlights = highlights.filter(page_number=page_number)
        
        highlights = highlights.order_by('page_number', 'created_at')
        
        return Response({
            'highlights': [
                {
                    'id': highlight.id,
                    'page_number': highlight.page_number,
                    'start_position': highlight.start_position,
                    'end_position': highlight.end_position,
                    'selected_text': highlight.selected_text,
                    'color': highlight.color,
                    'note': highlight.note,
                    'created_at': highlight.created_at
                }
                for highlight in highlights
            ]
        })
    
    @action(detail=False, methods=['put'])
    def update_highlight(self, request):
        """Update a highlight"""
        user_id = self.get_user_id()
        highlight_id = request.data.get('highlight_id')
        color = request.data.get('color')
        note = request.data.get('note')
        
        try:
            highlight = Highlight.objects.get(id=highlight_id, user_id=user_id)
            if color:
                highlight.color = color
            if note is not None:
                highlight.note = note
            highlight.save()
            
            return Response({
                'message': 'Highlight updated successfully',
                'highlight': {
                    'id': highlight.id,
                    'color': highlight.color,
                    'note': highlight.note
                }
            })
        except Highlight.DoesNotExist:
            return Response(
                {'error': 'Highlight not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['delete'])
    def delete_highlight(self, request):
        """Delete a highlight"""
        user_id = self.get_user_id()
        highlight_id = request.data.get('highlight_id')
        
        try:
            highlight = Highlight.objects.get(id=highlight_id, user_id=user_id)
            highlight.delete()
            return Response({'message': 'Highlight deleted successfully'})
        except Highlight.DoesNotExist:
            return Response(
                {'error': 'Highlight not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Note Features
    @action(detail=False, methods=['post'])
    def add_note(self, request):
        """Add a note to a page"""
        user_id = self.get_user_id()
        book_id = request.data.get('book_id')
        page_number = request.data.get('page_number')
        position = request.data.get('position', {})
        content = request.data.get('content', '')
        color = request.data.get('color', '#ffffff')
        is_private = request.data.get('is_private', True)
        
        book, error_response = self.verify_book_access(book_id)
        if error_response:
            return error_response
        
        note = Note.objects.create(
            user_id=user_id,
            book=book,
            page_number=page_number,
            position=position,
            content=content,
            color=color,
            is_private=is_private
        )
        
        return Response({
            'message': 'Note added successfully',
            'note': {
                'id': note.id,
                'page_number': note.page_number,
                'position': note.position,
                'content': note.content,
                'color': note.color,
                'is_private': note.is_private,
                'created_at': note.created_at
            }
        })
    
    @action(detail=False, methods=['get'])
    def get_notes(self, request):
        """Get all notes for a book"""
        user_id = self.get_user_id()
        book_id = request.GET.get('book_id')
        page_number = request.GET.get('page_number')
        
        book, error_response = self.verify_book_access(book_id)
        if error_response:
            return error_response
        
        notes = Note.objects.filter(user_id=user_id, book=book)
        if page_number:
            notes = notes.filter(page_number=page_number)
        
        notes = notes.order_by('page_number', 'created_at')
        
        return Response({
            'notes': [
                {
                    'id': note.id,
                    'page_number': note.page_number,
                    'position': note.position,
                    'content': note.content,
                    'color': note.color,
                    'is_private': note.is_private,
                    'created_at': note.created_at
                }
                for note in notes
            ]
        })
    
    @action(detail=False, methods=['put'])
    def update_note(self, request):
        """Update a note"""
        user_id = self.get_user_id()
        note_id = request.data.get('note_id')
        content = request.data.get('content')
        color = request.data.get('color')
        is_private = request.data.get('is_private')
        
        try:
            note = Note.objects.get(id=note_id, user_id=user_id)
            if content:
                note.content = content
            if color:
                note.color = color
            if is_private is not None:
                note.is_private = is_private
            note.save()
            
            return Response({
                'message': 'Note updated successfully',
                'note': {
                    'id': note.id,
                    'content': note.content,
                    'color': note.color,
                    'is_private': note.is_private
                }
            })
        except Note.DoesNotExist:
            return Response(
                {'error': 'Note not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['delete'])
    def delete_note(self, request):
        """Delete a note"""
        user_id = self.get_user_id()
        note_id = request.data.get('note_id')
        
        try:
            note = Note.objects.get(id=note_id, user_id=user_id)
            note.delete()
            return Response({'message': 'Note deleted successfully'})
        except Note.DoesNotExist:
            return Response(
                {'error': 'Note not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Screenshot Protection Features
    @action(detail=False, methods=['post'])
    def start_reading_session(self, request):
        """Start a reading session for screenshot tracking"""
        user_id = self.get_user_id()
        book_id = request.data.get('book_id')
        device_info = request.data.get('device_info', {})
        
        book, error_response = self.verify_book_access(book_id)
        if error_response:
            return error_response
        
        # Check if user is blocked from screenshots
        warning, created = ScreenshotWarning.objects.get_or_create(
            user_id=user_id,
            book=book,
            defaults={
                'warning_count': 0,
                'message': 'Screenshots are disabled to protect author copyright. Please respect intellectual property rights.'
            }
        )
        
        session = ReadingSession.objects.create(
            user_id=user_id,
            book=book,
            device_info=device_info
        )
        
        return Response({
            'session_id': session.id,
            'screenshot_protection': {
                'enabled': True,
                'warning_count': warning.warning_count,
                'is_blocked': warning.is_blocked,
                'message': warning.message
            }
        })
    
    @action(detail=False, methods=['post'])
    def report_screenshot_attempt(self, request):
        """Report a screenshot attempt"""
        user_id = self.get_user_id()
        session_id = request.data.get('session_id')
        book_id = request.data.get('book_id')
        
        try:
            session = ReadingSession.objects.get(id=session_id, user_id=user_id)
            book = Book.objects.get(id=book_id)
            
            # Increment screenshot attempts
            session.screenshot_attempts += 1
            session.save()
            
            # Update warning
            warning, created = ScreenshotWarning.objects.get_or_create(
                user_id=user_id,
                book=book,
                defaults={
                    'warning_count': 1,
                    'message': 'Screenshots are disabled to protect author copyright. Please respect intellectual property rights.'
                }
            )
            
            if not created:
                warning.warning_count += 1
                warning.last_warning = timezone.now()
                
                # Block user after 3 attempts
                if warning.warning_count >= 3:
                    warning.is_blocked = True
                    warning.message = "Multiple screenshot attempts detected. Your reading access has been temporarily restricted."
                
                warning.save()
            
            # Determine response based on warning count
            if warning.warning_count == 1:
                message = "Warning: Screenshots are not allowed. This is your first warning."
                severity = "warning"
            elif warning.warning_count == 2:
                message = "Final warning: Continued screenshot attempts will result in access restrictions."
                severity = "final_warning"
            else:
                message = "Access restricted due to repeated screenshot violations. Please contact support."
                severity = "blocked"
            
            return Response({
                'message': message,
                'severity': severity,
                'warning_count': warning.warning_count,
                'is_blocked': warning.is_blocked,
                'session_ended': warning.is_blocked
            })
            
        except (ReadingSession.DoesNotExist, Book.DoesNotExist):
            return Response(
                {'error': 'Invalid session or book'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def end_reading_session(self, request):
        """End a reading session"""
        user_id = self.get_user_id()
        session_id = request.data.get('session_id')
        pages_read = request.data.get('pages_read', 0)
        
        try:
            session = ReadingSession.objects.get(id=session_id, user_id=user_id)
            session.end_time = timezone.now()
            session.pages_read = pages_read
            
            # Calculate duration
            if session.end_time:
                duration = session.end_time - session.start_time
                session.duration_minutes = int(duration.total_seconds() / 60)
            
            session.save()
            
            return Response({
                'message': 'Reading session ended',
                'session_summary': {
                    'duration_minutes': session.duration_minutes,
                    'pages_read': session.pages_read,
                    'screenshot_attempts': session.screenshot_attempts
                }
            })
            
        except ReadingSession.DoesNotExist:
            return Response(
                {'error': 'Invalid session'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def get_all_annotations(self, request):
        """Get all annotations (bookmarks, highlights, notes) for a book"""
        user_id = self.get_user_id()
        book_id = request.GET.get('book_id')
        
        book, error_response = self.verify_book_access(book_id)
        if error_response:
            return error_response
        
        bookmarks = Bookmark.objects.filter(user_id=user_id, book=book)
        highlights = Highlight.objects.filter(user_id=user_id, book=book)
        notes = Note.objects.filter(user_id=user_id, book=book)
        
        return Response({
            'bookmarks': [
                {
                    'id': b.id,
                    'page_number': b.page_number,
                    'position': b.position,
                    'title': b.title,
                    'note': b.note,
                    'type': 'bookmark',
                    'created_at': b.created_at
                }
                for b in bookmarks
            ],
            'highlights': [
                {
                    'id': h.id,
                    'page_number': h.page_number,
                    'start_position': h.start_position,
                    'end_position': h.end_position,
                    'selected_text': h.selected_text,
                    'color': h.color,
                    'note': h.note,
                    'type': 'highlight',
                    'created_at': h.created_at
                }
                for h in highlights
            ],
            'notes': [
                {
                    'id': n.id,
                    'page_number': n.page_number,
                    'position': n.position,
                    'content': n.content,
                    'color': n.color,
                    'is_private': n.is_private,
                    'type': 'note',
                    'created_at': n.created_at
                }
                for n in notes
            ]
        })
