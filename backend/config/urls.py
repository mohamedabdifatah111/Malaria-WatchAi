from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

handler404 = "apps.core.views.not_found"
handler500 = "apps.core.views.server_error"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.geography.urls")),
    path("api/v1/", include("apps.prevalence.urls")),
    path("api/v1/", include("apps.population.urls")),
    path("api/v1/", include("apps.species.urls")),
    path("api/v1/", include("apps.drug_efficacy.urls")),
    path("api/v1/", include("apps.resistance.urls")),
    path("api/v1/", include("apps.assistant.urls")),
    path("api/v1/", include("apps.environment.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]