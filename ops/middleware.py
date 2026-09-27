import time
from .models import RequestMetric


class MetricsMiddleware:
    """
    Stores response time and status code for each request (simple monitoring).
    Excludes static/media to reduce noise.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        path = request.path or ""
        if not (path.startswith("/static/") or path.startswith("/media/")):
            try:
                RequestMetric.objects.create(
                    path=path[:255],
                    method=(request.method or "")[:10],
                    status_code=getattr(response, "status_code", 0) or 0,
                    duration_ms=max(duration_ms, 0),
                )
            except Exception:
                # Monitoring must never turn a healthy request into a 500 when the DB is unavailable.
                pass

        response["X-Response-Time-ms"] = str(duration_ms)
        return response
