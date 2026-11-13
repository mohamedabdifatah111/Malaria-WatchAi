from django.urls import path

from .views import PrevalenceListView, PrevalenceMapView, PrevalenceUncertaintyView

urlpatterns = [
    path("prevalence/", PrevalenceListView.as_view(), name="prevalence-list"),
    path("prevalence/map/", PrevalenceMapView.as_view(), name="prevalence-map"),
    path("prevalence/uncertainty/", PrevalenceUncertaintyView.as_view(), name="prevalence-uncertainty"),
]