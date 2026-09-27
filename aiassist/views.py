from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from tickets.models import Ticket
from .services import classify_text, suggest_kb, auto_response_steps

@login_required
@ratelimit(key="user", rate="30/m", block=True)
def suggest(request):
    text = request.GET.get("text", "")

    try:
        cat, pri, conf, debug = classify_text(text)
        kb = suggest_kb(text)
        steps = auto_response_steps(cat)

        return JsonResponse(
            {
                "category": cat,
                "priority": pri,
                "confidence": conf,
                "kb": kb,
                "steps": steps,
                "fallback": False,
                "debug": debug,  # optional; remove if you want
            }
        )
    except Exception:
        return JsonResponse(
            {
                "category": Ticket.Category.OTHER,
                "priority": Ticket.Priority.MEDIUM,
                "confidence": 0.0,
                "kb": [],
                "steps": [],
                "fallback": True,
            },
            status=200,
        )
