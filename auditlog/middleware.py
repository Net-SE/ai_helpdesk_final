import threading

_state = threading.local()


def get_audit_context():
    return getattr(_state, "ctx", {})


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _state.ctx = {
            "ip": request.META.get("REMOTE_ADDR"),
            "ua": (request.META.get("HTTP_USER_AGENT") or "")[:500],
        }
        return self.get_response(request)
