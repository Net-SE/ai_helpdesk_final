import json
from functools import wraps

from django.contrib.auth import authenticate
from django.db import connection
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from accounts.models import User
from aiassist.services import auto_response_steps, classify_text, suggest_kb
from auditlog.services import audit
from knowledgebase.models import KBArticle
from tickets.models import Ticket, TicketComment
from tickets.services import mark_resolved_fields_if_needed
from .auth import require_auth


def json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def user_payload(user):
    return {"id": user.id, "username": user.username, "role": user.role}


def ticket_payload(ticket, include_comments=False):
    data = {
        "id": ticket.id,
        "display_id": ticket.display_id(),
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "requester": user_payload(ticket.requester),
        "assigned_to": user_payload(ticket.assigned_to) if ticket.assigned_to else None,
        "resolution_note": ticket.resolution_note,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "first_response_at": ticket.first_response_at.isoformat() if ticket.first_response_at else None,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "due_response_at": ticket.due_response_at.isoformat() if ticket.due_response_at else None,
        "due_resolve_at": ticket.due_resolve_at.isoformat() if ticket.due_resolve_at else None,
        "is_archived": ticket.is_archived,
        "ai": {
            "category": ticket.ai_category,
            "priority": ticket.ai_priority,
            "confidence": ticket.ai_confidence,
        },
    }
    if include_comments:
        comments = ticket.comments.select_related("author").order_by("created_at")
        data["comments"] = [
            {
                "id": c.id,
                "author": user_payload(c.author),
                "message": c.message,
                "is_internal": c.is_internal,
                "created_at": c.created_at.isoformat(),
            }
            for c in comments
        ]
    return data


def can_view_ticket(user, ticket):
    if user.is_superuser or user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.MANAGER:
        return True
    if user.role == User.Role.TECHNICIAN:
        return ticket.assigned_to_id in (None, user.id)
    return ticket.requester_id == user.id


def api_auth(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        user, error = require_auth(request)
        if error:
            return error
        request.api_user = user
        return view(request, *args, **kwargs)
    return wrapped


@csrf_exempt
def health(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_status = "ok"
    except Exception:
        db_status = "error"
    status = 200 if db_status == "ok" else 503
    return JsonResponse({"ok": status == 200, "database": db_status, "service": "IT Assist API"}, status=status)


@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    data = json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    user = authenticate(request, username=data.get("username", ""), password=data.get("password", ""))
    if not user:
        return JsonResponse({"detail": "Invalid username or password."}, status=401)
    return JsonResponse({"user": user_payload(user), "authentication": "Use HTTP Basic Authentication for subsequent API requests."})


@api_auth
@csrf_exempt
def tickets_api(request):
    user = request.api_user
    if request.method == "GET":
        qs = Ticket.objects.filter(is_archived=False).select_related("requester", "assigned_to").order_by("-created_at")
        q = request.GET.get("q", "").strip()
        status = request.GET.get("status", "").strip()
        category = request.GET.get("category", "").strip()
        priority = request.GET.get("priority", "").strip()
        if user.role == User.Role.REQUESTER:
            qs = qs.filter(requester=user)
        elif user.role == User.Role.TECHNICIAN:
            qs = qs.filter(Q(assigned_to=user) | Q(assigned_to__isnull=True))
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(id__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if category:
            qs = qs.filter(category=category)
        if priority:
            qs = qs.filter(priority=priority)
        limit = min(max(int(request.GET.get("limit", 20)), 1), 100)
        return JsonResponse({"count": qs.count(), "results": [ticket_payload(t) for t in qs[:limit]]})

    if request.method == "POST":
        data = json_body(request)
        if data is None:
            return JsonResponse({"detail": "Invalid JSON."}, status=400)
        title = str(data.get("title", "")).strip()
        description = str(data.get("description", "")).strip()
        if not title or not description:
            return JsonResponse({"detail": "title and description are required."}, status=400)
        category, priority, confidence, debug = classify_text(f"{title}\n{description}")
        requested_category = data.get("category")
        requested_priority = data.get("priority")
        if requested_category in Ticket.Category.values:
            category = requested_category
        if requested_priority in Ticket.Priority.values:
            priority = requested_priority
        ticket = Ticket.objects.create(
            requester=user,
            title=title,
            description=description,
            category=category,
            priority=priority,
            ai_category=category,
            ai_priority=priority,
            ai_confidence=confidence,
        )
        steps = auto_response_steps(category)
        if steps:
            from aiassist.services import get_ai_user
            TicketComment.objects.create(ticket=ticket, author=get_ai_user(), message="AI Auto-response (suggested steps):\n" + "\n".join(f"- {s}" for s in steps), is_internal=False)
        audit(request, "TICKET_CREATE", ticket, f"Created {ticket.display_id()} via API")
        return JsonResponse({"ticket": ticket_payload(ticket, include_comments=True), "ai_debug": debug}, status=201)

    return JsonResponse({"detail": "Method not allowed."}, status=405)


@api_auth
@csrf_exempt
def ticket_detail_api(request, pk):
    ticket = Ticket.objects.filter(pk=pk, is_archived=False).select_related("requester", "assigned_to").first()
    if not ticket or not can_view_ticket(request.api_user, ticket):
        return JsonResponse({"detail": "Ticket not found."}, status=404)
    if request.method == "GET":
        data = ticket_payload(ticket, include_comments=True)
        if request.api_user.role == User.Role.REQUESTER:
            data["comments"] = [c for c in data["comments"] if not c["is_internal"]]
        return JsonResponse(data)
    if request.method == "PATCH":
        data = json_body(request)
        if data is None:
            return JsonResponse({"detail": "Invalid JSON."}, status=400)
        if request.api_user.role == User.Role.REQUESTER and ticket.requester_id != request.api_user.id:
            return JsonResponse({"detail": "Forbidden."}, status=403)
        for field in ("title", "description"):
            if field in data:
                value = str(data[field]).strip()
                if not value:
                    return JsonResponse({"detail": f"{field} cannot be empty."}, status=400)
                setattr(ticket, field, value)
        if request.api_user.is_manager():
            if data.get("category") in Ticket.Category.values:
                ticket.category = data["category"]
            if data.get("priority") in Ticket.Priority.values:
                ticket.priority = data["priority"]
        ticket.full_clean()
        ticket.save()
        audit(request, "TICKET_UPDATE", ticket, f"Updated {ticket.display_id()} via API")
        return JsonResponse(ticket_payload(ticket, include_comments=True))
    return JsonResponse({"detail": "Method not allowed."}, status=405)


@api_auth
@csrf_exempt
def ticket_status_api(request, pk):
    if request.method != "PATCH":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    ticket = Ticket.objects.filter(pk=pk, is_archived=False).first()
    if not ticket:
        return JsonResponse({"detail": "Ticket not found."}, status=404)
    user = request.api_user
    if user.role not in {User.Role.TECHNICIAN, User.Role.MANAGER, User.Role.ADMIN}:
        return JsonResponse({"detail": "Forbidden."}, status=403)
    if user.role == User.Role.TECHNICIAN and ticket.assigned_to_id not in (None, user.id):
        return JsonResponse({"detail": "You may only update assigned or unassigned tickets."}, status=403)
    data = json_body(request)
    if data is None or data.get("status") not in Ticket.Status.values:
        return JsonResponse({"detail": "A valid status is required."}, status=400)
    ticket.status = data["status"]
    if "resolution_note" in data:
        ticket.resolution_note = str(data["resolution_note"] or "")
    try:
        ticket.full_clean()
        ticket.save()
        mark_resolved_fields_if_needed(ticket)
    except Exception as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    audit(request, "TICKET_STATUS", ticket, f"Status -> {ticket.status} via API")
    return JsonResponse(ticket_payload(ticket))


@api_auth
@csrf_exempt
def ticket_assign_api(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user = request.api_user
    if not user.is_manager():
        return JsonResponse({"detail": "Forbidden."}, status=403)
    ticket = Ticket.objects.filter(pk=pk, is_archived=False).first()
    if not ticket:
        return JsonResponse({"detail": "Ticket not found."}, status=404)
    data = json_body(request)
    try:
        technician = User.objects.get(pk=data.get("technician_id"), role=User.Role.TECHNICIAN, is_active=True)
    except (User.DoesNotExist, TypeError, ValueError):
        return JsonResponse({"detail": "A valid technician_id is required."}, status=400)
    ticket.assigned_to = technician
    ticket.save(update_fields=["assigned_to", "updated_at"])
    audit(request, "TICKET_ASSIGN", ticket, f"Assigned to {technician.username} via API")
    return JsonResponse(ticket_payload(ticket))


@api_auth
@csrf_exempt
def ticket_comment_api(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    ticket = Ticket.objects.filter(pk=pk, is_archived=False).first()
    if not ticket or not can_view_ticket(request.api_user, ticket):
        return JsonResponse({"detail": "Ticket not found."}, status=404)
    data = json_body(request)
    message = str(data.get("message", "")).strip() if data else ""
    if not message:
        return JsonResponse({"detail": "message is required."}, status=400)
    is_internal = bool(data.get("is_internal", False))
    if is_internal and request.api_user.role == User.Role.REQUESTER:
        return JsonResponse({"detail": "Requesters cannot create internal comments."}, status=403)
    comment = TicketComment.objects.create(ticket=ticket, author=request.api_user, message=message, is_internal=is_internal)
    return JsonResponse({"id": comment.id, "ticket_id": ticket.id, "author": user_payload(request.api_user), "message": comment.message, "is_internal": comment.is_internal, "created_at": comment.created_at.isoformat()}, status=201)


@api_auth
@csrf_exempt
def kb_api(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    qs = KBArticle.objects.filter(is_archived=False)
    if request.api_user.role == User.Role.REQUESTER:
        qs = qs.filter(is_public=True)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))
    return JsonResponse({"count": qs.count(), "results": [{"id": a.id, "title": a.title, "body": a.body, "is_public": a.is_public, "created_at": a.created_at.isoformat()} for a in qs.order_by("-created_at")[:50]]})


@api_auth
@csrf_exempt
def kb_detail_api(request, pk):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    article = KBArticle.objects.filter(pk=pk, is_archived=False).first()
    if not article or (request.api_user.role == User.Role.REQUESTER and not article.is_public):
        return JsonResponse({"detail": "Article not found."}, status=404)
    return JsonResponse({"id": article.id, "title": article.title, "body": article.body, "is_public": article.is_public, "created_at": article.created_at.isoformat()})


@api_auth
@csrf_exempt
def ai_suggest_api(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    data = json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    text = f"{data.get('title', '')}\n{data.get('description', '')}".strip()
    if not text:
        return JsonResponse({"detail": "title or description is required."}, status=400)
    category, priority, confidence, debug = classify_text(text)
    return JsonResponse({"engine": "rule-based AI", "category": category, "priority": priority, "confidence": confidence, "troubleshooting_steps": auto_response_steps(category), "knowledge_base": suggest_kb(text), "debug": debug})


@api_auth
def dashboard_api(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    if not request.api_user.is_manager():
        return JsonResponse({"detail": "Forbidden."}, status=403)
    qs = Ticket.objects.filter(is_archived=False)
    return JsonResponse({
        "total": qs.count(),
        "open": qs.filter(status=Ticket.Status.OPEN).count(),
        "in_progress": qs.filter(status=Ticket.Status.IN_PROGRESS).count(),
        "resolved": qs.filter(status=Ticket.Status.RESOLVED).count(),
        "closed": qs.filter(status=Ticket.Status.CLOSED).count(),
        "by_category": list(qs.values("category").annotate(count=__import__("django.db.models", fromlist=["Count"]).Count("id"))),
        "by_priority": list(qs.values("priority").annotate(count=__import__("django.db.models", fromlist=["Count"]).Count("id"))),
    })
