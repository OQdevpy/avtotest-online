from django.urls import path

from . import views

urlpatterns = [
    path("sections/", views.SectionListView.as_view(), name="section-list"),
    path("sections/<int:pk>/", views.SectionDetailView.as_view(), name="section-detail"),

    path("lessons/", views.LessonListView.as_view(), name="lesson-list"),
    path("lessons/<int:pk>/", views.LessonDetailView.as_view(), name="lesson-detail"),

    path("topics/", views.TopicListView.as_view(), name="topic-list"),
    path("topics/<int:pk>/", views.TopicDetailView.as_view(), name="topic-detail"),

    path("tickets/", views.TicketListView.as_view(), name="ticket-list"),
    path("tickets/stats/", views.TicketStatsView.as_view(), name="ticket-stats"),
    path("tickets/<int:number>/", views.TicketDetailView.as_view(), name="ticket-detail"),

    path("exam/generate/", views.ExamGenerateView.as_view(), name="exam-generate"),
]
