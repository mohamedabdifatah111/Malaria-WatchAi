from django.urls import path

from .views import SpeciesListView

urlpatterns = [
    path("species/", SpeciesListView.as_view(), name="species-list"),
]