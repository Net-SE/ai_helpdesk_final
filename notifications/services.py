from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

from .models import Notification

User = get_user_model()


def notify(user, title, body=""):
    Notification.objects.create(user=user, title=title, body=body)

    if getattr(user, "email", ""):
        send_mail(
            subject=title,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )


def notify_ticket_event(ticket, event: str):
    targets = {ticket.requester}
    if ticket.assigned_to:
        targets.add(ticket.assigned_to)

    managers = User.objects.filter(role__in=[User.Role.MANAGER, User.Role.ADMIN])
    for m in managers:
        targets.add(m)

    title = f"{ticket.display_id()} - {event}"
    body = (
        f"Title: {ticket.title}\nStatus: {ticket.status}\nPriority: {ticket.priority}"
    )

    for u in targets:
        notify(u, title, body)
