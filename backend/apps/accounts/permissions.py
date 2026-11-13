from rest_framework.permissions import BasePermission

REVIEWER_GROUP = "reviewer"


class IsReviewer(BasePermission):
    """Authenticated, active user in the 'reviewer' group. Superusers are not exempt."""

    message = "Reviewer permission is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.groups.filter(name=REVIEWER_GROUP).exists()
        )