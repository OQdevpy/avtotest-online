from django.urls import path

from . import views

urlpatterns = [
    path("lesson-results/", views.LessonResultListCreateView.as_view(), name="lesson-results"),
    path("ticket-results/", views.TicketResultListCreateView.as_view(), name="ticket-results"),
    path("exam-attempts/", views.ExamAttemptListCreateView.as_view(), name="exam-attempts"),

    path("mistakes/", views.MistakeListView.as_view(), name="mistake-list"),
    path("mistakes/<int:pk>/resolve/", views.MistakeResolveView.as_view(), name="mistake-resolve"),

    path("saved/", views.SavedQuestionListCreateView.as_view(), name="saved-list"),
    path("saved/<int:question_id>/", views.SavedQuestionDeleteView.as_view(), name="saved-delete"),

    path("stats/", views.StatsView.as_view(), name="stats"),
    path("reset/", views.ResetProgressView.as_view(), name="progress-reset"),
]
