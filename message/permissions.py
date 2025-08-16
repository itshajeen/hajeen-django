from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow read-only access to authenticated users 
        if request.method in permissions.SAFE_METHODS:
            return True
        # Allow write access only to admins or superusers 
        return request.user and request.user.is_superuser or request.user.is_staff 
