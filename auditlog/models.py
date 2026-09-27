from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class AuditLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    message = models.TextField(blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.created_at} {self.action} {self.object_type}:{self.object_id}"


# from django.conf import settings
# from django.core.mail import send_mail
# from accounts.models import User
# from .models import Notification


# def notify(user, title, body=""):
#     Notification.objects.create(user=user, title=title, body=body)
#     if user.email:
#         send_mail(
#             subject=title,
#             message=body,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[user.email],
#             fail_silently=True,
#         )


# def notify_ticket_event(ticket, event: str):
#     targets = {ticket.requester}
#     if ticket.assigned_to:
#         targets.add(ticket.assigned_to)

#     # managers also get notified (optional)
#     managers = User.objects.filter(role__in=[User.Role.MANAGER, User.Role.ADMIN])
#     for m in managers:
#         targets.add(m)

#     title = f"{ticket.display_id()} - {event}"
#     body = (
#         f"Title: {ticket.title}\nStatus: {ticket.status}\nPriority: {ticket.priority}"
#     )

#     for u in targets:
#         notify(u, title, body)
