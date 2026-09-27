from django.utils import timezone
from .models import Ticket, TicketComment


def mark_first_response_if_needed(comment: TicketComment):
    t = comment.ticket
    if t.first_response_at:
        return
    # first public reply from IT staff counts
    if (
        not comment.is_internal
        and getattr(comment.author, "is_it_staff", lambda: False)()
    ):
        t.first_response_at = timezone.now()
        t.save(update_fields=["first_response_at"])


def mark_resolved_fields_if_needed(ticket: Ticket):
    from django.utils import timezone

    if ticket.status == Ticket.Status.RESOLVED and not ticket.resolved_at:
        ticket.resolved_at = timezone.now()
        ticket.save(update_fields=["resolved_at"])
    if ticket.status == Ticket.Status.CLOSED and not ticket.closed_at:
        ticket.closed_at = timezone.now()
        ticket.save(update_fields=["closed_at"])
