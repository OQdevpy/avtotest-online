from django.urls import path

from . import teacher_views

urlpatterns = [
    path("students/", teacher_views.TeacherStudentListView.as_view(),
         name="teacher-student-list"),
    path("students/<int:pk>/stats/", teacher_views.TeacherStudentStatsView.as_view(),
         name="teacher-student-stats"),
    path("stats/", teacher_views.TeacherStatsView.as_view(), name="teacher-stats"),
]
