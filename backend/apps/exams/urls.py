from django.urls import path

from . import views

urlpatterns = [
    path("start/", views.ExamStartView.as_view(), name="exam-start"),
    path("", views.ExamSessionListView.as_view(), name="exam-session-list"),
    path("<int:pk>/", views.ExamSessionDetailView.as_view(), name="exam-session-detail"),
    path("<int:pk>/answer/", views.ExamAnswerView.as_view(), name="exam-answer"),
    path("<int:pk>/finish/", views.ExamFinishView.as_view(), name="exam-finish"),
]
