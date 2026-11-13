from django.urls import path

from .views import CountryListView, RegionDetailView, RegionListView

urlpatterns = [
    path("countries/", CountryListView.as_view(), name="country-list"),
    path("regions/", RegionListView.as_view(), name="region-list"),
    path("regions/<int:pk>/", RegionDetailView.as_view(), name="region-detail"),
]