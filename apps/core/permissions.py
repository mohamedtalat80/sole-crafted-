"""
Reusable DRF permission classes.

Design (ISP): each permission class has a single, focused check.
"""
from rest_framework.permissions import BasePermission


class IsCustomer(BasePermission):
    """Allow access only to users with account_type == 'customer'."""

    message = "Only customer accounts can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.account_type == "customer"
        )


class IsAdminAccount(BasePermission):
    """
    Allow access only to users with account_type == 'admin'.

    Note: distinct from Django's is_staff / is_superuser flags.
    Use this for API endpoints reserved for platform administrators.
    """

    message = "Only admin accounts can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.account_type == "admin"
        )
