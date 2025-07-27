from rest_framework import permissions



class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow read access for any authenticated user, and write access only for admins.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:  # GET, HEAD, OPTIONS
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff or request.user.is_superuser
    

# IsGuardianOrReadOnly permission class 
class IsGuardianOwnDependent(permissions.BasePermission):
    """
    Allow guardians to create dependents, but only see, update, or delete their own dependents.
    """

    def has_permission(self, request, view):
        # Allow only authenticated users with guardian profile
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, 'guardian'))

    def has_object_permission(self, request, view, obj):
        # Only allow access to dependents owned by the guardian
        return hasattr(request.user, 'guardian') and obj.guardian == request.user.guardian


