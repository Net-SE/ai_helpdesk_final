from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
import psutil


def healthz(request):
    ok = True
    db = "ok"
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
    except Exception:
        ok = False
        db = "unavailable"
    return JsonResponse({"ok": ok, "db": db}, status=200 if ok else 503)


def system_metrics(request):
    if not request.user.is_authenticated or not request.user.is_manager():
        return JsonResponse({"detail": "Forbidden"}, status=403)
    return JsonResponse(
        {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }
    )


def error_400(request, exception=None):
    return render(request, "errors/400.html", status=400)


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    return render(request, "errors/500.html", status=500)
