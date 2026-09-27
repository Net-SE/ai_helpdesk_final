from django.urls import path
from .views import dashboard_view, ticket_report_csv

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("tickets.csv", ticket_report_csv, name="ticket_report_csv"),
]
