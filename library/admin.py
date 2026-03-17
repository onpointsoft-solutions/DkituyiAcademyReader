from django.contrib import admin
from .models import UserLibrary, ReadingProgress, ReadingSession


@admin.register(UserLibrary)
class UserLibraryAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'book', 'purchase_date', 'is_active', 'access_expires')
    list_filter = ('is_active', 'purchase_date', 'access_expires')
    search_fields = ('book__title', 'book__author__name')
    readonly_fields = ('purchase_date',)
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing existing object
            return self.readonly_fields + ('user_id', 'book')
        return self.readonly_fields


@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'book', 'current_page', 'total_pages', 'progress_percentage', 'is_completed', 'last_read')
    list_filter = ('is_completed', 'last_read')
    search_fields = ('book__title', 'book__author__name')
    readonly_fields = ('last_read',)
    
    fieldsets = (
        ('Reading Info', {
            'fields': ('user_id', 'book', 'current_page', 'total_pages')
        }),
        ('Progress', {
            'fields': ('progress_percentage', 'is_completed', 'reading_time_minutes', 'last_read')
        }),
    )


@admin.register(ReadingSession)
class ReadingSessionAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'book', 'start_page', 'end_page', 'duration_minutes', 'start_time', 'end_time')
    list_filter = ('start_time', 'duration_minutes')
    search_fields = ('book__title', 'book__author__name')
    readonly_fields = ('start_time', 'end_time')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing existing object
            return self.readonly_fields + ('user_id', 'book', 'start_page')
        return self.readonly_fields
