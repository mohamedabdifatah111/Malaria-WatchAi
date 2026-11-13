from django.urls import path

from .views import ResistanceListView, ResistanceTrendListView

urlpatterns = [
    path("resistance/", ResistanceListView.as_view(), name="resistance-list"),
    path("resistance/trends/", ResistanceTrendListView.as_view(), name="resistance-trends"),
]