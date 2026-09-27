from django.urls import path
from . import views

urlpatterns = [
    path("", views.notification_list, name="notification_list"),
    path("read/<int:pk>/", views.notification_mark_read, name="notification_mark_read"),
    path(
        "read-all/", views.notification_mark_all_read, name="notification_mark_all_read"
    ),
    path(
        "api/unread/",
        views.notification_unread_summary,
        name="notification_unread_summary",
    ),
]
