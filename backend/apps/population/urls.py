from django.urls import path

from .views import PopulationAtRiskListView

urlpatterns = [
    path("population-at-risk/", PopulationAtRiskListView.as_view(), name="population-at-risk"),
]