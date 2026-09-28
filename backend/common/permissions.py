"""Rolga asoslangan ruxsat sinflari.

`User.role` biznes huquqini belgilaydi; Django'ning `is_staff` esa faqat admin
paneliga kirishni. Ikkisi bir-biridan mustaqil.
"""

from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    message = "Bu amal faqat o'quvchilar uchun."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.role == user.Role.STUDENT)


class IsTeacherOrAdmin(BasePermission):
    message = "Bu amal faqat o'qituvchi va shef uchun."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_teacher)


class IsAdminRole(BasePermission):
    message = "Bu amal faqat shef uchun."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_content_admin)
