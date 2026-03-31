"""
Production-ready tests for User API endpoints.

This module provides comprehensive test coverage for all user API endpoints
with proper setup, mocking, and assertions for production environments.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book, Author, Category
from library.models import UserLibrary, ReadingProgress

User = get_user_model()


class BaseUserAPITestCase(APITestCase):
    """Base test case with common setup for User API tests."""
    
    def setUp(self):
        """Set up test data and authentication."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.client.force_authenticate(user=self.user)
        
        # Create test author and book
        self.author = Author.objects.create(name='Test Author')
        self.book = Book.objects.create(
            title='Test Book',
            author=self.author,
            pages=200,
            price=10.00
        )
        
        # Add book to user library
        self.library_entry = UserLibrary.objects.create(
            user=self.user,
            book=self.book,
            is_active=True
        )
        
        # Create reading progress
        self.reading_progress = ReadingProgress.objects.create(
            user=self.user,
            book=self.book,
            current_page=50,
            total_pages=200,
            progress_percentage=25.0
        )


class UserStatsViewTests(BaseUserAPITestCase):
    """Test cases for UserStatsView."""
    
    def test_get_user_stats_success(self):
        """Test successful retrieval of user statistics."""
        url = reverse('user_api:user_stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Statistics retrieved successfully')
        
        stats = data['data']
        self.assertIn('totalBooks', stats)
        self.assertIn('booksRead', stats)
        self.assertIn('readingTimeHours', stats)
        self.assertIn('readingStreak', stats)
        self.assertIn('achievements', stats)
        
        # Verify calculated values
        self.assertEqual(stats['totalBooks'], 1)
        self.assertEqual(stats['booksRead'], 0)  # Progress is 25%, not 100%
        self.assertGreaterEqual(stats['readingTimeHours'], 0)
        self.assertGreaterEqual(stats['readingStreak'], 0)
        self.assertGreaterEqual(stats['achievements'], 0)
    
    def test_get_user_stats_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        self.client.force_authenticate(user=None)
        url = reverse('user_api:user_stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_user_stats_with_completed_book(self):
        """Test stats calculation with completed books."""
        # Mark book as completed
        self.reading_progress.progress_percentage = 100.0
        self.reading_progress.save()
        
        url = reverse('user_api:user_stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        stats = data['data']
        
        self.assertEqual(stats['booksRead'], 1)
        self.assertGreater(stats['achievements'], 0)  # Should have at least 1 achievement
    
    @patch('user_api.views.logger')
    def test_get_user_stats_logging(self, mock_logger):
        """Test that logging is properly configured."""
        url = reverse('user_api:user_stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_logger.info.assert_called_once()
        
        # Check that log contains expected context
        call_args = mock_logger.info.call_args
        self.assertIn('user_id', call_args[1]['extra'])
        self.assertIn('username', call_args[1]['extra'])
        self.assertIn('stats', call_args[1]['extra'])


class RecentBooksViewTests(BaseUserAPITestCase):
    """Test cases for RecentBooksView."""
    
    def test_get_recent_books_success(self):
        """Test successful retrieval of recent books."""
        url = reverse('user_api:recent_books')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Recent books retrieved successfully')
        
        books_data = data['data']
        self.assertIn('results', books_data)
        self.assertIn('count', books_data)
        
        results = books_data['results']
        self.assertEqual(len(results), 1)
        
        book = results[0]
        self.assertEqual(book['id'], self.book.id)
        self.assertEqual(book['title'], self.book.title)
        self.assertEqual(book['author_name'], self.author.name)
        self.assertEqual(book['reading_progress'], 25.0)
        self.assertEqual(book['current_page'], 50)
        self.assertFalse(book['is_completed'])
    
    def test_get_recent_books_empty_library(self):
        """Test retrieval when user has no books."""
        # Remove library entry
        self.library_entry.delete()
        
        url = reverse('user_api:recent_books')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        results = data['data']['results']
        self.assertEqual(len(results), 0)
        self.assertEqual(data['data']['count'], 0)
    
    def test_get_recent_books_performance_optimization(self):
        """Test that database queries are optimized."""
        url = reverse('user_api:recent_books')
        
        with self.assertNumQueries(2):  # Should be 2 optimized queries
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserProfileViewTests(BaseUserAPITestCase):
    """Test cases for UserProfileView."""
    
    def test_get_user_profile_success(self):
        """Test successful retrieval of user profile."""
        url = reverse('user_api:user_profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Profile retrieved successfully')
        
        profile = data['data']
        self.assertEqual(profile['id'], self.user.id)
        self.assertEqual(profile['username'], self.user.username)
        self.assertEqual(profile['email'], self.user.email)
        self.assertEqual(profile['first_name'], self.user.first_name)
        self.assertEqual(profile['last_name'], self.user.last_name)
        self.assertIn('library_count', profile)
        self.assertIn('books_read', profile)
        self.assertIn('reading_hours', profile)
        self.assertIn('reading_streak', profile)
        self.assertIn('achievements', profile)
    
    def test_update_user_profile_success(self):
        """Test successful update of user profile."""
        url = reverse('user_api:user_profile')
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'bio': 'Updated bio',
            'favorite_genres': 'Fiction, Mystery',
            'reading_goal': 5
        }
        
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Profile updated successfully')
        
        # Verify user was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
    
    def test_update_user_profile_invalid_username(self):
        """Test profile update with invalid username."""
        # Create another user with the username we want to use
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        url = reverse('user_api:user_profile')
        update_data = {
            'username': 'otheruser'  # Already taken
        }
        
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Username is already taken', data['message'])
    
    def test_update_user_profile_empty_fields(self):
        """Test profile update with empty required fields."""
        url = reverse('user_api:user_profile')
        update_data = {
            'username': '',
            'email': ''
        }
        
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('cannot be empty', data['message'])


class ReadingProgressViewTests(BaseUserAPITestCase):
    """Test cases for ReadingProgressView."""
    
    def test_update_reading_progress_success(self):
        """Test successful update of reading progress."""
        url = reverse('user_api:update_reading_progress')
        update_data = {
            'book_id': self.book.id,
            'progress': 50.0,
            'current_page': 100
        }
        
        response = self.client.post(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('Progress updated successfully', data['message'])
        
        progress_data = data['data']
        self.assertEqual(progress_data['progress'], 50.0)
        self.assertEqual(progress_data['current_page'], 100)
        self.assertFalse(progress_data['is_completed'])
        
        # Verify database was updated
        self.reading_progress.refresh_from_db()
        self.assertEqual(self.reading_progress.progress_percentage, 50.0)
        self.assertEqual(self.reading_progress.current_page, 100)
    
    def test_update_reading_progress_invalid_book(self):
        """Test progress update for book not in library."""
        url = reverse('user_api:update_reading_progress')
        update_data = {
            'book_id': 99999,  # Non-existent book
            'progress': 50.0
        }
        
        response = self.client.post(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Book not found in your library', data['message'])
    
    def test_update_reading_progress_invalid_progress(self):
        """Test progress update with invalid progress values."""
        url = reverse('user_api:update_reading_progress')
        
        # Test progress > 100
        update_data = {
            'book_id': self.book.id,
            'progress': 150.0
        }
        
        response = self.client.post(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('between 0 and 100', data['message'])
        
        # Test progress < 0
        update_data['progress'] = -10.0
        response = self.client.post(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid progress type
        update_data['progress'] = 'invalid'
        response = self.client.post(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_update_reading_progress_missing_book_id(self):
        """Test progress update without book ID."""
        url = reverse('user_api:update_reading_progress')
        update_data = {
            'progress': 50.0
        }
        
        response = self.client.post(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Book ID is required', data['message'])
    
    def test_update_reading_progress_completion(self):
        """Test progress update that marks book as completed."""
        url = reverse('user_api:update_reading_progress')
        update_data = {
            'book_id': self.book.id,
            'progress': 100.0,
            'current_page': 200
        }
        
        response = self.client.post(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        progress_data = data['data']
        self.assertTrue(progress_data['is_completed'])


class UserAPIIntegrationTests(BaseUserAPITestCase):
    """Integration tests for User API endpoints."""
    
    def test_complete_user_workflow(self):
        """Test complete user workflow from stats to progress update."""
        # 1. Get initial stats
        stats_url = reverse('user_api:user_stats')
        stats_response = self.client.get(stats_url)
        self.assertEqual(stats_response.status_code, status.HTTP_200_OK)
        
        initial_stats = stats_response.json()['data']
        self.assertEqual(initial_stats['booksRead'], 0)
        
        # 2. Get recent books
        books_url = reverse('user_api:recent_books')
        books_response = self.client.get(books_url)
        self.assertEqual(books_response.status_code, status.HTTP_200_OK)
        
        books = books_response.json()['data']['results']
        self.assertEqual(len(books), 1)
        
        # 3. Update reading progress to completion
        progress_url = reverse('user_api:update_reading_progress')
        progress_data = {
            'book_id': books[0]['id'],
            'progress': 100.0,
            'current_page': 200
        }
        
        progress_response = self.client.post(progress_url, progress_data, format='json')
        self.assertEqual(progress_response.status_code, status.HTTP_200_OK)
        
        # 4. Verify stats updated
        updated_stats_response = self.client.get(stats_url)
        updated_stats = updated_stats_response.json()['data']
        
        self.assertEqual(updated_stats['booksRead'], 1)
        self.assertGreater(updated_stats['achievements'], initial_stats['achievements'])
    
    def test_error_handling_consistency(self):
        """Test that all endpoints return consistent error format."""
        endpoints = [
            ('user_api:user_stats', 'get'),
            ('user_api:recent_books', 'get'),
            ('user_api:user_profile', 'get'),
            ('user_api:update_reading_progress', 'post')
        ]
        
        # Test unauthenticated access
        self.client.force_authenticate(user=None)
        
        for endpoint_name, method in endpoints:
            url = reverse(endpoint_name)
            
            if method == 'get':
                response = self.client.get(url)
            else:
                response = self.client.post(url, {}, format='json')
            
            # All should return 401 with consistent format
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            
            # Check error format consistency (if response has JSON)
            if response.content:
                try:
                    data = response.json()
                    self.assertIn('success', data)
                    self.assertFalse(data['success'])
                    self.assertIn('message', data)
                except json.JSONDecodeError:
                    pass  # Some auth errors might return HTML


class UserAPIPerformanceTests(BaseUserAPITestCase):
    """Performance tests for User API endpoints."""
    
    def test_stats_endpoint_performance(self):
        """Test that stats endpoint uses optimized queries."""
        # Create multiple books and progress entries
        for i in range(10):
            book = Book.objects.create(
                title=f'Book {i}',
                author=self.author,
                pages=100
            )
            UserLibrary.objects.create(user=self.user, book=book, is_active=True)
            ReadingProgress.objects.create(
                user=self.user,
                book=book,
                current_page=50,
                total_pages=100,
                progress_percentage=50.0
            )
        
        url = reverse('user_api:user_stats')
        
        # Should use minimal queries due to aggregation
        with self.assertNumQueries(2):
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_recent_books_endpoint_performance(self):
        """Test that recent books endpoint uses optimized queries."""
        # Create multiple books
        for i in range(20):
            book = Book.objects.create(
                title=f'Book {i}',
                author=self.author,
                pages=100
            )
            UserLibrary.objects.create(user=self.user, book=book, is_active=True)
        
        url = reverse('user_api:recent_books')
        
        # Should use optimized queries with select_related and prefetch_related
        with self.assertNumQueries(2):
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        results = data['data']['results']
        self.assertEqual(len(results), 20)  # All books should be returned
