from rest_framework import permissions
from students.models import Student

class HasValidTokenParam(permissions.BasePermission):
    """
    Checks if 'token' query param exists and matches an active student.
    """
    def has_permission(self, request, view):
        token = request.query_params.get('token')
        if not token:
            return False
        return Student.objects.filter(token=token, is_active=True).exists()
