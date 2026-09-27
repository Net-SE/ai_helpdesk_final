from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="api_health"),
    path("auth/login/", views.login_api, name="api_login"),
    path("tickets/", views.tickets_api, name="api_tickets"),
    path("tickets/<int:pk>/", views.ticket_detail_api, name="api_ticket_detail"),
    path("tickets/<int:pk>/status/", views.ticket_status_api, name="api_ticket_status"),
    path("tickets/<int:pk>/assign/", views.ticket_assign_api, name="api_ticket_assign"),
    path("tickets/<int:pk>/comments/", views.ticket_comment_api, name="api_ticket_comment"),
    path("kb/", views.kb_api, name="api_kb"),
    path("kb/<int:pk>/", views.kb_detail_api, name="api_kb_detail"),
    path("ai/suggest/", views.ai_suggest_api, name="api_ai_suggest"),
    path("dashboard/", views.dashboard_api, name="api_dashboard"),
]
