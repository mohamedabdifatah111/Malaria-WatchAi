from django.urls import path

from .views import CurrentWeatherView, WeatherHistoryView

urlpatterns = [
    path("environment/current/", CurrentWeatherView.as_view(), name="environment-current"),
    path("environment/history/", WeatherHistoryView.as_view(), name="environment-history"),
]