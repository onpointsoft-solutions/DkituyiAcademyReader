from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ReaderViewSet, unlock_page, get_unlocked_pages, create_note, get_notes, delete_note, create_bookmark, get_bookmarks, delete_bookmark
from .annotation_views import ReadingFeaturesViewSet
from .simple_views import SimpleReaderViewSet
from .pdf_reader_views import PDFReaderViewSet

router = SimpleRouter()
router.register(r'', ReaderViewSet, basename='reader')

urlpatterns = [
    path('', include(router.urls)),
    # Page unlocking endpoints
    path('features/unlock_page/', unlock_page, name='unlock_page'),
    path('features/unlocked_pages/<int:book_id>/', get_unlocked_pages, name='get_unlocked_pages'),
    
    # Notes endpoints
    path('features/notes/', create_note, name='create_note'),
    path('features/notes/<int:book_id>/', get_notes, name='get_notes'),
    path('features/notes/<int:note_id>/', delete_note, name='delete_note'),
    
    # Bookmarks endpoints
    path('features/bookmarks/', create_bookmark, name='create_bookmark'),
    path('features/bookmarks/<int:book_id>/', get_bookmarks, name='get_bookmarks'),
    path('features/bookmarks/<int:bookmark_id>/', delete_bookmark, name='delete_bookmark'),
]