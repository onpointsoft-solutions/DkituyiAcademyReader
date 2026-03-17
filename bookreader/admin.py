from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin


class BookReaderAdminSite(AdminSite):
    """Custom admin site for BookReader platform"""
    site_header = _('BookReader Administration')
    site_title = _('BookReader Admin')
    index_title = _('Welcome to BookReader Admin Panel')
    
    def has_permission(self, request):
        """
        Only superusers can access the admin
        """
        return request.user.is_superuser


# Create custom admin instance
bookreader_admin = BookReaderAdminSite(name='bookreader_admin')

# Register models with custom admin
bookreader_admin.register(User, UserAdmin)
bookreader_admin.register(Group, GroupAdmin)

# Import and register book-related models
from books.models import Book, Author, Category, BookReview
from books.admin import BookAdmin, AuthorAdmin, CategoryAdmin
from library.models import UserLibrary, ReadingProgress, ReadingSession
from library.admin import UserLibraryAdmin, ReadingProgressAdmin, ReadingSessionAdmin

bookreader_admin.register(Book, BookAdmin)
bookreader_admin.register(Author, AuthorAdmin)
bookreader_admin.register(Category, CategoryAdmin)
bookreader_admin.register(BookReview)
bookreader_admin.register(UserLibrary, UserLibraryAdmin)
bookreader_admin.register(ReadingProgress, ReadingProgressAdmin)
bookreader_admin.register(ReadingSession, ReadingSessionAdmin)


# Customize default admin site as well
admin.site.site_header = _('BookReader Administration')
admin.site.site_title = _('BookReader Admin')
admin.site.index_title = _('BookReader Administration Panel')
