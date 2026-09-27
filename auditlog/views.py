from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render

from .models import AuditLog


@login_required
def audit_list(request):
    if not request.user.is_manager():
        raise Http404()

    qs = AuditLog.objects.all().order_by("-created_at")

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(action__icontains=q)
            | Q(object_type__icontains=q)
            | Q(object_id__icontains=q)
            | Q(message__icontains=q)
        )

    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "auditlog/audit_list.html", {"page": page, "q": q})
