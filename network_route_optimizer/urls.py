"""
Root URL configuration.

Docs are served at:
  /api/schema/          — raw OpenAPI 3.0 schema (YAML/JSON)
  /api/schema/swagger/  — Swagger UI
  /api/schema/redoc/    — ReDoc UI
"""
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("", include("routes.urls")),
    # OpenAPI schema + interactive docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]