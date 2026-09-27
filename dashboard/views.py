from collections import defaultdict
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from ops.models import RequestMetric
from tickets.models import Ticket


def _avg(numbers):
    """Return average of valid numeric values."""
    numbers = [number for number in numbers if number is not None]
    return round(sum(numbers) / len(numbers), 2) if numbers else 0


@login_required
def dashboard_view(request):
    # Only IT Manager/Admin can access dashboard
    if not request.user.is_manager():
        raise Http404()

    tickets = Ticket.objects.filter(is_archived=False)

    # ----------------------------
    # 1. Ticket summary counts
    # ----------------------------
    total_tickets = tickets.count()
    open_tickets = tickets.filter(status=Ticket.Status.OPEN).count()
    in_progress_tickets = tickets.filter(status=Ticket.Status.IN_PROGRESS).count()
    resolved_tickets = tickets.filter(status=Ticket.Status.RESOLVED).count()
    closed_tickets = tickets.filter(status=Ticket.Status.CLOSED).count()

    # ----------------------------
    # 2. Chart data
    # ----------------------------
    by_status = list(
        tickets.values("status").annotate(c=Count("id")).order_by("status")
    )

    by_category = list(
        tickets.values("category").annotate(c=Count("id")).order_by("category")
    )

    by_priority = list(
        tickets.values("priority").annotate(c=Count("id")).order_by("priority")
    )

    # ----------------------------
    # 3. Response and resolution time
    # ----------------------------
    responded_tickets = tickets.exclude(first_response_at__isnull=True)
    resolved_ticket_queryset = tickets.exclude(resolved_at__isnull=True)

    avg_first_response = _avg(
        [ticket.first_response_minutes for ticket in responded_tickets]
    )

    avg_resolution = _avg(
        [ticket.resolution_minutes for ticket in resolved_ticket_queryset]
    )

    # ----------------------------
    # 4. SLA compliance percentage
    # ----------------------------
    response_total = responded_tickets.count()
    resolve_total = resolved_ticket_queryset.count()

    response_ok = sum(1 for ticket in responded_tickets if ticket.met_response_sla)

    resolve_ok = sum(1 for ticket in resolved_ticket_queryset if ticket.met_resolve_sla)

    response_compliance = (
        round((response_ok / response_total) * 100, 2) if response_total else 0
    )

    resolve_compliance = (
        round((resolve_ok / resolve_total) * 100, 2) if resolve_total else 0
    )

    # ----------------------------
    # 5. SLA breach lists
    # ----------------------------
    now = timezone.now()

    response_breaches = tickets.filter(
        first_response_at__isnull=True,
        due_response_at__lt=now,
    ).order_by("due_response_at")[:10]

    resolve_breaches = tickets.filter(
        resolved_at__isnull=True,
        due_resolve_at__lt=now,
    ).order_by("due_resolve_at")[:10]

    # ----------------------------
    # 6. Technician performance
    # ----------------------------
    # Group tickets assigned to each technician.
    technician_data = defaultdict(
        lambda: {
            "username": "",
            "assigned_count": 0,
            "resolved_count": 0,
            "avg_resolution_minutes": 0,
            "resolution_times": [],
        }
    )

    assigned_tickets = tickets.exclude(assigned_to__isnull=True).select_related(
        "assigned_to"
    )

    for ticket in assigned_tickets:
        technician_id = ticket.assigned_to_id

        technician_data[technician_id]["username"] = ticket.assigned_to.username
        technician_data[technician_id]["assigned_count"] += 1

        if ticket.resolved_at:
            technician_data[technician_id]["resolved_count"] += 1

            if ticket.resolution_minutes is not None:
                technician_data[technician_id]["resolution_times"].append(
                    ticket.resolution_minutes
                )

    technician_stats = []

    for data in technician_data.values():
        data["avg_resolution_minutes"] = _avg(data["resolution_times"])
        del data["resolution_times"]
        technician_stats.append(data)

    technician_stats.sort(
        key=lambda technician: technician["assigned_count"],
        reverse=True,
    )

    # ----------------------------
    # 7. OPS monitoring metrics
    # Last 1 hour request information
    # ----------------------------
    since = timezone.now() - timedelta(hours=1)

    request_metrics = RequestMetric.objects.filter(created_at__gte=since)

    total_requests = request_metrics.count()

    # 400+ is client/server error response
    failed_requests = request_metrics.filter(status_code__gte=400).count()

    # 500+ is server error response
    server_errors = request_metrics.filter(status_code__gte=500).count()

    avg_resp_ms = (
        request_metrics.aggregate(avg_duration=Avg("duration_ms"))["avg_duration"] or 0
    )

    error_rate = (
        round((failed_requests / total_requests) * 100, 2) if total_requests else 0
    )

    # ----------------------------
    # Render dashboard
    # ----------------------------
    return render(
        request,
        "dashboard/dashboard.html",
        {
            # Ticket summary
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "in_progress_tickets": in_progress_tickets,
            "resolved_tickets": resolved_tickets,
            "closed_tickets": closed_tickets,
            # Charts
            "by_status": by_status,
            "by_category": by_category,
            "by_priority": by_priority,
            # SLA
            "avg_first_response": avg_first_response,
            "avg_resolution": avg_resolution,
            "response_compliance": response_compliance,
            "resolve_compliance": resolve_compliance,
            "response_breaches": response_breaches,
            "resolve_breaches": resolve_breaches,
            # Technician performance
            "technician_stats": technician_stats,
            # OPS metrics
            "total_requests": total_requests,
            "failed_requests": failed_requests,
            "server_errors": server_errors,
            "avg_resp_ms": round(avg_resp_ms, 2),
            "error_rate": error_rate,
        },
    )


@login_required
def ticket_report_csv(request):
    if not request.user.is_manager():
        raise Http404()

    import csv

    tickets = Ticket.objects.filter(is_archived=False).select_related(
        "requester", "assigned_to"
    ).order_by("-created_at")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="ticket_report.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Ticket", "Title", "Requester", "Technician", "Category",
        "Priority", "Status", "Created At", "First Response At",
        "Resolved At", "First Response Minutes", "Resolution Minutes",
        "Response SLA", "Resolve SLA",
    ])

    for ticket in tickets:
        writer.writerow([
            ticket.display_id(),
            ticket.title,
            ticket.requester.username,
            ticket.assigned_to.username if ticket.assigned_to else "",
            ticket.get_category_display(),
            ticket.get_priority_display(),
            ticket.get_status_display(),
            ticket.created_at,
            ticket.first_response_at or "",
            ticket.resolved_at or "",
            ticket.first_response_minutes or "",
            ticket.resolution_minutes or "",
            "Met" if ticket.met_response_sla else ("Pending" if not ticket.first_response_at else "Breached"),
            "Met" if ticket.met_resolve_sla else ("Pending" if not ticket.resolved_at else "Breached"),
        ])

    return response
