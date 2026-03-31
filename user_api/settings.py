"""
User API Settings

Production-ready configuration settings for the User API module.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import os


class UserAPISettings:
    """
    Settings wrapper for User API configuration.
    
    Provides centralized configuration management with fallback defaults
    and environment variable support for production deployments.
    """
    
    def __init__(self):
        self._settings = {
            # API Configuration
            'MAX_RECENT_BOOKS': getattr(settings, 'USER_API_MAX_RECENT_BOOKS', 20),
            'READING_TIME_PER_PAGE': getattr(settings, 'USER_API_READING_TIME_PER_PAGE', 2),  # minutes
            'STREAK_CALCULATION_DAYS': getattr(settings, 'USER_API_STREAK_CALCULATION_DAYS', 30),
            'ACHIEVEMENT_MILESTONES': getattr(settings, 'USER_API_ACHIEVEMENT_MILESTONES', {
                'books': [1, 5, 10, 25, 50],
                'streaks': [7, 30, 100]
            }),
            
            # Security Settings
            'ALLOW_PROFILE_IMAGE_UPLOAD': getattr(settings, 'USER_API_ALLOW_PROFILE_IMAGE_UPLOAD', True),
            'MAX_PROFILE_IMAGE_SIZE': getattr(settings, 'USER_API_MAX_PROFILE_IMAGE_SIZE', 5 * 1024 * 1024),  # 5MB
            'ALLOWED_PROFILE_IMAGE_TYPES': getattr(settings, 'USER_API_ALLOWED_PROFILE_IMAGE_TYPES', 
                                                  ['image/jpeg', 'image/png', 'image/webp']),
            
            # Performance Settings
            'USE_SELECT_RELATED': getattr(settings, 'USER_API_USE_SELECT_RELATED', True),
            'USE_PREFETCH_RELATED': getattr(settings, 'USER_API_USE_PREFETCH_RELATED', True),
            'QUERY_TIMEOUT': getattr(settings, 'USER_API_QUERY_TIMEOUT', 30),  # seconds
            
            # Logging Settings
            'LOG_LEVEL': getattr(settings, 'USER_API_LOG_LEVEL', 'INFO'),
            'STRUCTURED_LOGGING': getattr(settings, 'USER_API_STRUCTURED_LOGGING', True),
            'LOG_REQUEST_ID': getattr(settings, 'USER_API_LOG_REQUEST_ID', True),
            'LOG_USER_CONTEXT': getattr(settings, 'USER_API_LOG_USER_CONTEXT', True),
            
            # Rate Limiting
            'ENABLE_RATE_LIMITING': getattr(settings, 'USER_API_ENABLE_RATE_LIMITING', True),
            'RATE_LIMIT_REQUESTS': getattr(settings, 'USER_API_RATE_LIMIT_REQUESTS', 100),
            'RATE_LIMIT_WINDOW': getattr(settings, 'USER_API_RATE_LIMIT_WINDOW', 3600),  # 1 hour
            
            # Caching
            'ENABLE_CACHING': getattr(settings, 'USER_API_ENABLE_CACHING', False),
            'CACHE_TIMEOUT': getattr(settings, 'USER_API_CACHE_TIMEOUT', 300),  # 5 minutes
            'CACHE_KEY_PREFIX': getattr(settings, 'USER_API_CACHE_KEY_PREFIX', 'user_api'),
        }
    
    def __getattr__(self, name: str):
        """Get setting value with fallback."""
        if name in self._settings:
            return self._settings[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def get(self, name: str, default=None):
        """Get setting value with custom default."""
        return self._settings.get(name, default)
    
    def validate_settings(self) -> None:
        """Validate critical settings for production use."""
        errors = []
        
        # Validate numeric settings
        numeric_settings = {
            'MAX_RECENT_BOOKS': (1, 100),
            'READING_TIME_PER_PAGE': (1, 60),
            'STREAK_CALCULATION_DAYS': (1, 365),
            'MAX_PROFILE_IMAGE_SIZE': (1024, 50 * 1024 * 1024),
            'QUERY_TIMEOUT': (5, 300),
            'RATE_LIMIT_REQUESTS': (1, 10000),
            'RATE_LIMIT_WINDOW': (60, 86400),
            'CACHE_TIMEOUT': (1, 3600),
        }
        
        for setting, (min_val, max_val) in numeric_settings.items():
            value = self.get(setting)
            if not isinstance(value, (int, float)) or not (min_val <= value <= max_val):
                errors.append(f"{setting} must be between {min_val} and {max_val}")
        
        # Validate list settings
        list_settings = {
            'ALLOWED_PROFILE_IMAGE_TYPES': list,
            'ACHIEVEMENT_MILESTONES': dict,
        }
        
        for setting, expected_type in list_settings.items():
            value = self.get(setting)
            if not isinstance(value, expected_type):
                errors.append(f"{setting} must be of type {expected_type.__name__}")
        
        # Validate boolean settings
        boolean_settings = [
            'ALLOW_PROFILE_IMAGE_UPLOAD',
            'USE_SELECT_RELATED',
            'USE_PREFETCH_RELATED',
            'STRUCTURED_LOGGING',
            'LOG_REQUEST_ID',
            'LOG_USER_CONTEXT',
            'ENABLE_RATE_LIMITING',
            'ENABLE_CACHING',
        ]
        
        for setting in boolean_settings:
            value = self.get(setting)
            if not isinstance(value, bool):
                errors.append(f"{setting} must be a boolean")
        
        if errors:
            raise ImproperlyConfigured(
                f"User API configuration errors: {'; '.join(errors)}"
            )


# Global settings instance
user_api_settings = UserAPISettings()

# Validate settings on import
if not settings.DEBUG:
    user_api_settings.validate_settings()
