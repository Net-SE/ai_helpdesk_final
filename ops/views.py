from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import render
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from accounts.models import User
from .models import RequestMetric


@login_required
def ops_dashboard(request):
    """Operational dashboard for managers/admins: latency, error rate and resources."""
    if not request.user.is_manager():
        raise PermissionDenied

    since = timezone.now() - timedelta(hours=1)
    metrics = RequestMetric.objects.filter(created_at__gte=since)
    total = metrics.count()
    errors = metrics.filter(status_code__gte=500).count()

    return render(
        request,
        "ops/dashboard.html",
        {
            "since": since,
            "request_count": total,
            "error_count": errors,
            "error_rate": round((errors / total) * 100, 2) if total else 0,
            "avg_response_ms": round(metrics.aggregate(v=Avg("duration_ms"))["v"] or 0, 2),
            "slowest": metrics.order_by("-duration_ms")[:10],
            "status_counts": metrics.values("status_code").annotate(count=Count("id")).order_by("-count"),
        },
    )
