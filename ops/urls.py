from django.urls import path
from .views import ops_dashboard

urlpatterns = [
    path("", ops_dashboard, name="ops_dashboard"),
]
