# User API - Production Ready

A production-ready Django REST Framework API for user dashboard and profile functionality with comprehensive logging, error handling, and performance optimization.

## Features

- **User Statistics**: Comprehensive reading metrics and achievements
- **Recent Books**: Library management with reading progress tracking
- **Profile Management**: Secure user profile updates with validation
- **Reading Progress**: Real-time progress tracking with completion detection
- **Production Logging**: Structured logging with security context
- **Performance Optimized**: Database query optimization and caching support
- **Security First**: Proper authentication, validation, and error handling

## API Endpoints

### User Statistics
```
GET /api/user/stats/
```
Returns comprehensive user reading statistics including:
- Total books in library
- Books completed
- Reading time estimation
- Reading streak
- Achievement count

### Recent Books
```
GET /api/user/recent-books/
```
Returns user's recent books with reading progress:
- Book details (title, author, cover)
- Current reading progress
- Last read timestamp
- Completion status

### User Profile
```
GET /api/user/profile/
PUT /api/user/profile/
```
Get or update user profile information:
- Basic user information
- Reading statistics
- Custom profile fields
- Achievement data

### Reading Progress
```
POST /api/user/reading-progress/
```
Update reading progress for a specific book:
- Progress percentage (0-100)
- Current page number
- Completion detection

## Response Format

All endpoints follow a consistent JSON response format:

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // Response data
  }
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error description",
  "data": null
}
```

## Authentication

All endpoints require JWT authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

## Performance Optimizations

### Database Query Optimization
- **select_related**: Optimizes foreign key relationships
- **prefetch_related**: Optimizes many-to-many relationships
- **aggregate**: Reduces multiple queries to single aggregation
- **bulk operations**: Minimizes database round trips

### Caching Support
Configure caching in Django settings:

```python
USER_API_ENABLE_CACHING = True
USER_API_CACHE_TIMEOUT = 300  # 5 minutes
USER_API_CACHE_KEY_PREFIX = 'user_api'
```

### Rate Limiting
Protect against abuse with rate limiting:

```python
USER_API_ENABLE_RATE_LIMITING = True
USER_API_RATE_LIMIT_REQUESTS = 100
USER_API_RATE_LIMIT_WINDOW = 3600  # 1 hour
```

## Logging Configuration

### Structured Logging
The API uses structured logging for production environments:

```python
USER_API_LOG_LEVEL = 'INFO'
USER_API_STRUCTURED_LOGGING = True
USER_API_LOG_USER_CONTEXT = True
USER_API_LOG_REQUEST_ID = True
```

### Log Format
Logs are structured for easy parsing and monitoring:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "user_api.views",
  "message": "User statistics retrieved successfully",
  "user_id": 123,
  "username": "testuser",
  "stats": {...}
}
```

## Security Features

### Input Validation
- All user inputs are validated and sanitized
- Progress values are range-checked (0-100)
- Required fields are enforced
- Username uniqueness is verified

### Authentication & Authorization
- JWT token validation
- User ownership verification for library access
- Permission-based access control

### Data Protection
- Sensitive data is never logged
- Error messages don't expose internal details
- SQL injection protection through ORM

## Configuration

### Settings
Configure the User API in your Django settings:

```python
# API Configuration
USER_API_MAX_RECENT_BOOKS = 20
USER_API_READING_TIME_PER_PAGE = 2  # minutes per page
USER_API_STREAK_CALCULATION_DAYS = 30

# Security Settings
USER_API_ALLOW_PROFILE_IMAGE_UPLOAD = True
USER_API_MAX_PROFILE_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
USER_API_ALLOWED_PROFILE_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

# Performance Settings
USER_API_USE_SELECT_RELATED = True
USER_API_USE_PREFETCH_RELATED = True
USER_API_QUERY_TIMEOUT = 30
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python manage.py test user_api

# Run specific test class
python manage.py test user_api.tests.UserStatsViewTests

# Run with coverage
python manage.py test user_api --coverage=user_api
```

### Test Coverage
- Unit tests for all endpoints
- Integration tests for complete workflows
- Performance tests for query optimization
- Error handling validation
- Authentication and authorization tests

## Monitoring and Observability

### Health Checks
Monitor API health with built-in logging:

```python
# Check for errors in logs
grep "ERROR" /var/log/django/user_api.log

# Monitor response times
grep "response_time" /var/log/django/user_api.log
```

### Metrics
Key metrics to monitor:
- Response time per endpoint
- Error rate
- Authentication failures
- Database query performance
- User activity patterns

## Migration from Function-Based Views

The API has been refactored from function-based views to class-based views for better maintainability:

### Old (Deprecated)
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    # Implementation
```

### New (Recommended)
```python
class UserStatsView(BaseAPIView):
    def get(self, request):
        # Implementation with better error handling and logging
```

### Migration Path
1. Update URL patterns to use class-based views
2. Update client code to handle new response format
3. Remove deprecated function-based views
4. Update tests to use new endpoints

## Deployment Considerations

### Production Checklist
- [ ] Configure proper logging levels
- [ ] Enable rate limiting
- [ ] Set up monitoring and alerting
- [ ] Configure caching if needed
- [ ] Review security settings
- [ ] Run performance tests
- [ ] Set up database backups
- [ ] Configure load balancing

### Environment Variables
Use environment variables for sensitive configuration:

```bash
export USER_API_LOG_LEVEL=INFO
export USER_API_ENABLE_RATE_LIMITING=true
export USER_API_RATE_LIMIT_REQUESTS=100
```

## Troubleshooting

### Common Issues

#### 500 Internal Server Error
Check logs for detailed error information:
```bash
tail -f /var/log/django/user_api.log
```

#### Authentication Failures
Verify JWT token is valid and not expired:
```python
# Check token payload
import jwt
token = 'your_jwt_token'
payload = jwt.decode(token, options={'verify_signature': False})
print(payload)
```

#### Performance Issues
Monitor database queries:
```python
# Enable query logging
import logging
logging.getLogger('django.db.backends').setLevel(logging.DEBUG)
```

### Debug Mode
Enable debug logging for development:
```python
USER_API_LOG_LEVEL = 'DEBUG'
USER_API_STRUCTURED_LOGGING = False
```

## Contributing

### Code Standards
- Follow PEP8 style guidelines
- Use type hints for all functions
- Add comprehensive docstrings
- Include unit tests for new features
- Use structured logging throughout

### Pull Request Process
1. Create feature branch from main
2. Add tests for new functionality
3. Ensure all tests pass
4. Update documentation
5. Submit pull request with description

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the project repository
- Check the troubleshooting section
- Review the test cases for usage examples
