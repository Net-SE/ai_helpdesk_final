from django.urls import path
from .views import healthz, system_metrics

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("metrics/", system_metrics, name="system_metrics"),
]
