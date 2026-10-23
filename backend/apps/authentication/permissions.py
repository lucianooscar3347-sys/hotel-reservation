from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import User


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == User.Role.ADMIN)


class IsStaffRole(BasePermission):
    """Administrateur ou réceptionniste."""

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_staff_member)


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user.is_authenticated and request.user.role == User.Role.ADMIN)
