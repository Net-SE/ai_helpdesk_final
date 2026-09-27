from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import Notification


@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "notifications/notification_list.html", {"page": page})


@login_required
def notification_mark_read(request, pk: int):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return redirect("notification_list")


@login_required
def notification_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notification_list")


@login_required
def notification_unread_summary(request):
    unread_qs = Notification.objects.filter(user=request.user, is_read=False).order_by(
        "-created_at"
    )
    unread_count = unread_qs.count()
    latest = list(unread_qs.values("id", "title", "created_at")[:5])
    return JsonResponse({"unread_count": unread_count, "latest": latest})
