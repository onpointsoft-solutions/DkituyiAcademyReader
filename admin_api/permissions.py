from rest_framework.permissions import BasePermission
from django.contrib.auth.models import User

print("🔍 DEBUG: IsStaffUser class loaded")

class IsStaffUser(BasePermission):
    """Only allow staff/superuser to access admin API."""
    message = "Staff access required."

    def __init__(self):
        print("🔍 DEBUG: IsStaffUser.__init__ called")
        super().__init__()

    def has_permission(self, request, view):
        print(f"🔍 DEBUG: IsStaffUser.has_permission called")
        print(f"🔍 DEBUG: hasattr(request, 'user_payload'): {hasattr(request, 'user_payload')}")
        print(f"🔍 DEBUG: request.user_payload: {getattr(request, 'user_payload', None)}")
        
        # Check if user is authenticated via JWT middleware
        if hasattr(request, 'user_payload') and request.user_payload:
            user_id = request.user_payload.get('user_id')
            print(f"🔍 DEBUG: user_id from JWT: {user_id}")
            if user_id:
                try:
                    # Get the actual user from database to check staff status
                    user = User.objects.get(id=user_id)
                    print(f"🔍 DEBUG: User from DB - {user.username}, is_staff: {user.is_staff}, is_superuser: {user.is_superuser}")
                    result = user.is_staff or user.is_superuser
                    print(f"🔍 DEBUG: Permission result: {result}")
                    return result
                except User.DoesNotExist:
                    print(f"🔍 DEBUG: User.DoesNotExist for user_id: {user_id}")
                    return False
        else:
            print(f"🔍 DEBUG: No user_payload found")
        
        # Fallback to standard Django user check
        print(f"🔍 DEBUG: Fallback to Django user check")
        has_user = bool(request.user)
        is_auth = hasattr(request.user, 'is_authenticated') and request.user.is_authenticated
        is_staff = hasattr(request.user, 'is_staff') and request.user.is_staff
        is_superuser = hasattr(request.user, 'is_superuser') and request.user.is_superuser
        
        print(f"🔍 DEBUG: Django user - exists: {has_user}, authenticated: {is_auth}, staff: {is_staff}, superuser: {is_superuser}")
        
        result = (
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )
        print(f"🔍 DEBUG: Fallback permission result: {result}")
        return result
