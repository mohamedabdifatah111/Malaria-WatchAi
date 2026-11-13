from django.urls import path

from .views import DrugEfficacyListView

urlpatterns = [
    path("drugs/efficacy/", DrugEfficacyListView.as_view(), name="drug-efficacy"),
]