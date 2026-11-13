from django.urls import path

from .views import AssistantLogListView, BriefCreateView, BriefReviewView

urlpatterns = [
    path("assistant/brief/", BriefCreateView.as_view(), name="assistant-brief"),
    path("assistant/review/", BriefReviewView.as_view(), name="assistant-review"),
    path("assistant/logs/", AssistantLogListView.as_view(), name="assistant-logs"),
]