from .models import AuditLog
from .middleware import get_audit_context


def audit(request, action: str, obj=None, message: str = ""):
    ctx = get_audit_context()
    AuditLog.objects.create(
        actor=(
            getattr(request, "user", None)
            if getattr(request, "user", None) and request.user.is_authenticated
            else None
        ),
        action=action,
        object_type=obj.__class__.__name__ if obj else "",
        object_id=str(getattr(obj, "pk", "")) if obj else "",
        message=message,
        ip_address=ctx.get("ip"),
        user_agent=ctx.get("ua", ""),
    )
