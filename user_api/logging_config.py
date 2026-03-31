"""
Production logging configuration for User API.

This module provides structured logging configuration optimized for
production environments with proper log levels and formatting.
"""

import logging
import sys
from typing import Dict, Any


class UserAPIFormatter(logging.Formatter):
    """
    Custom formatter for user API logs with structured output.
    
    Formats logs in a structured way that's easy to parse in production
    while remaining readable for development.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Get extra fields if they exist
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 
                          'funcName', 'created', 'msecs', 'relativeCreated', 
                          'thread', 'threadName', 'processName', 'process',
                          'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                extra_fields[key] = value
        
        # Build structured log message
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields if present
        if extra_fields:
            log_data.update(extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Format as JSON-like string (without importing json to avoid dependency)
        parts = []
        for key, value in log_data.items():
            if isinstance(value, str):
                parts.append(f'"{key}": "{value}"')
            else:
                parts.append(f'"{key}": {value}')
        
        return '{' + ', '.join(parts) + '}'


def setup_user_api_logging(log_level: str = 'INFO') -> None:
    """
    Set up logging configuration for the User API.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    # Create logger
    logger = logging.getLogger('user_api')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = UserAPIFormatter()
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for the user API.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(f'user_api.{name}')
