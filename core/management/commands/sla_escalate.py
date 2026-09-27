from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from tickets.models import Ticket
from notifications.services import notify

User = get_user_model()

RISK_RESPONSE_MINUTES = 5  # alert when <= 5 minutes remaining to response SLA
RISK_RESOLVE_MINUTES = 15  # alert when <= 15 minutes remaining to resolve SLA


class Command(BaseCommand):
    help = "Send SLA risk escalation alerts (response/resolve approaching breach)."

    def handle(self, *args, **options):
        now = timezone.now()

        managers = list(User.objects.filter(role__in=["MANAGER", "ADMIN"]))

        # 1) Response SLA risk
        resp_candidates = Ticket.objects.filter(
            is_archived=False,
            first_response_at__isnull=True,
            due_response_at__isnull=False,
            status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS],
        )

        for t in resp_candidates:
            remaining = t.due_response_at - now
            if remaining <= timedelta(
                minutes=RISK_RESPONSE_MINUTES
            ) and remaining > timedelta(seconds=0):
                if t.response_risk_alerted_at:
                    continue
                title = f"SLA Response Risk: {t.display_id()}"
                body = (
                    f"Ticket is close to response SLA deadline.\n"
                    f"Title: {t.title}\n"
                    f"Priority: {t.priority}\n"
                    f"Due Response: {t.due_response_at}\n"
                )
                targets = set(managers)
                if t.assigned_to:
                    targets.add(t.assigned_to)
                targets.add(t.requester)

                for u in targets:
                    notify(u, title, body)

                t.response_risk_alerted_at = now
                t.save(update_fields=["response_risk_alerted_at"])

        # 2) Resolve SLA risk
        res_candidates = Ticket.objects.filter(
            is_archived=False,
            resolved_at__isnull=True,
            due_resolve_at__isnull=False,
            status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS],
        )

        for t in res_candidates:
            remaining = t.due_resolve_at - now
            if remaining <= timedelta(
                minutes=RISK_RESOLVE_MINUTES
            ) and remaining > timedelta(seconds=0):
                if t.resolve_risk_alerted_at:
                    continue
                title = f"SLA Resolve Risk: {t.display_id()}"
                body = (
                    f"Ticket is close to resolve SLA deadline.\n"
                    f"Title: {t.title}\n"
                    f"Priority: {t.priority}\n"
                    f"Due Resolve: {t.due_resolve_at}\n"
                )
                targets = set(managers)
                if t.assigned_to:
                    targets.add(t.assigned_to)
                targets.add(t.requester)

                for u in targets:
                    notify(u, title, body)

                t.resolve_risk_alerted_at = now
                t.save(update_fields=["resolve_risk_alerted_at"])

        # 3) Breach alert (once)
        breach_candidates = Ticket.objects.filter(
            is_archived=False,
            breach_alerted_at__isnull=True,
        )

        for t in breach_candidates:
            breached = t.is_sla_response_breached or t.is_sla_resolve_breached
            if not breached:
                continue

            title = f"SLA BREACHED: {t.display_id()}"
            body = (
                f"Ticket has breached SLA.\n"
                f"Title: {t.title}\n"
                f"Status: {t.status}\n"
                f"Priority: {t.priority}\n"
                f"Response Due: {t.due_response_at}\n"
                f"Resolve Due: {t.due_resolve_at}\n"
            )
            targets = set(managers)
            if t.assigned_to:
                targets.add(t.assigned_to)
            targets.add(t.requester)

            for u in targets:
                notify(u, title, body)

            t.breach_alerted_at = now
            t.save(update_fields=["breach_alerted_at"])

        self.stdout.write(self.style.SUCCESS("SLA escalation check completed."))
