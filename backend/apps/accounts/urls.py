from django.urls import path

from .views import TokenLoginView

urlpatterns = [
    path("auth/token/", TokenLoginView.as_view(), name="auth-token"),
]