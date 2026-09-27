from django.urls import path
from . import views

urlpatterns = [
    path("", views.ticket_list, name="ticket_list"),
    path("search/", views.helpdesk_search, name="helpdesk_search"),
    path("tickets/create/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/assign/", views.ticket_assign, name="ticket_assign"),
    path(
        "tickets/<int:pk>/status/",
        views.ticket_update_status,
        name="ticket_update_status",
    ),
    path(
        "tickets/<int:pk>/comment/", views.ticket_add_comment, name="ticket_add_comment"
    ),
    path(
        "attachments/<int:attachment_id>/download/",
        views.attachment_download,
        name="attachment_download",
    ),
    path("tickets/<int:pk>/archive/", views.ticket_archive, name="ticket_archive"),
    path("tickets/archived/", views.ticket_archived_list, name="ticket_archived_list"),
]
