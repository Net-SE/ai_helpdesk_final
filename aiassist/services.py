import re
from difflib import SequenceMatcher
from django.contrib.auth import get_user_model

from tickets.models import Ticket
from knowledgebase.models import KBArticle

User = get_user_model()


KEYWORDS = {
    Ticket.Category.NETWORK: [
        "internet",
        "wifi",
        "wi-fi",
        "lan",
        "network",
        "slow",
        "disconnect",
        "router",
        "dns",
    ],
    Ticket.Category.ACCOUNT: [
        "password",
        "login",
        "account",
        "locked",
        "mfa",
        "otp",
        "access",
        "permission",
        "reset",
    ],
    Ticket.Category.HARDWARE: [
        "printer",
        "mouse",
        "keyboard",
        "monitor",
        "pc",
        "laptop",
        "hardware",
        "scanner",
    ],
    Ticket.Category.SOFTWARE: [
        "install",
        "error",
        "crash",
        "software",
        "excel",
        "word",
        "outlook",
        "update",
        "bug",
    ],
}

PRIORITY_HINTS = {
    Ticket.Priority.CRITICAL: [
        "server down",
        "down",
        "urgent",
        "critical",
        "cannot work",
        "production",
    ],
    Ticket.Priority.HIGH: ["asap", "high", "important", "immediately"],
    Ticket.Priority.MEDIUM: ["medium"],
    Ticket.Priority.LOW: ["low", "when you can", "not urgent", "whenever"],
}


def _normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def classify_text(text: str):
    """
    AI (rule-based) classification.
    Returns: (category, priority, confidence, debug)
    confidence: 0..1
    debug: shows which keywords matched (useful for demo/report)
    """
    t = _normalize(text)
    if not t:
        return (
            Ticket.Category.OTHER,
            Ticket.Priority.MEDIUM,
            0.0,
            {"category_hits": [], "priority_hits": []},
        )

    # Category scoring: count keyword hits
    best_cat = Ticket.Category.OTHER
    best_score = 0
    best_hits = []

    for cat, words in KEYWORDS.items():
        hits = [w for w in words if w in t]
        score = len(hits)
        if score > best_score:
            best_score = score
            best_cat = cat
            best_hits = hits

    # Priority: first match wins (CRITICAL -> HIGH -> MEDIUM -> LOW)
    best_pri = Ticket.Priority.MEDIUM
    pri_hits = []
    for pri in [
        Ticket.Priority.CRITICAL,
        Ticket.Priority.HIGH,
        Ticket.Priority.MEDIUM,
        Ticket.Priority.LOW,
    ]:
        words = PRIORITY_HINTS.get(pri, [])
        hits = [w for w in words if w in t]
        if hits:
            best_pri = pri
            pri_hits = hits
            break

    # Confidence heuristic
    # - more category hits => higher confidence
    # - priority hit gives extra confidence
    confidence = min(1.0, (best_score / 3.0) + (0.25 if pri_hits else 0.0))
    confidence = round(confidence, 2)

    debug = {
        "category_hits": best_hits,
        "priority_hits": pri_hits,
        "category_score": best_score,
    }
    return best_cat, best_pri, confidence, debug


def suggest_kb(text: str, limit=5):
    """
    Smart suggestions:
    1) title contains query (fast)
    2) if not enough, fuzzy title similarity (SequenceMatcher)
    """
    q = _normalize(text)
    if len(q) < 3:
        return []

    qs = KBArticle.objects.filter(is_archived=False, is_public=True)

    # 1) contains search
    primary = list(qs.filter(title__icontains=q)[:limit])
    results = primary[:]

    # 2) fuzzy match titles if not enough
    if len(results) < limit:
        remaining = limit - len(results)

        candidates = list(qs.values("id", "title")[:200])  # limit for speed
        scored = []
        for item in candidates:
            ratio = SequenceMatcher(a=q, b=_normalize(item["title"])).ratio()
            if ratio >= 0.35:
                scored.append((ratio, item["id"]))

        scored.sort(reverse=True)
        ids = [i for _, i in scored[:remaining]]
        more = list(qs.filter(id__in=ids))

        id_to_obj = {a.id: a for a in more}
        for _, _id in scored[:remaining]:
            if _id in id_to_obj:
                results.append(id_to_obj[_id])

    # Deduplicate and return payload
    seen = set()
    payload = []
    for a in results:
        if a.id in seen:
            continue
        seen.add(a.id)
        payload.append({"id": a.id, "title": a.title})
    return payload[:limit]


def auto_response_steps(category: str):
    if category == Ticket.Category.ACCOUNT:
        return [
            "Check Caps Lock and keyboard layout",
            "Try reset password",
            "Confirm username/email",
            "If locked, wait 10–15 minutes then retry",
        ]
    if category == Ticket.Category.NETWORK:
        return [
            "Check Wi‑Fi connected",
            "Disconnect/reconnect Wi‑Fi",
            "Try another website to confirm internet",
            "Run: ipconfig /flushdns (Windows)",
        ]
    if category == Ticket.Category.HARDWARE:
        return [
            "Check power cable",
            "Reconnect device (USB/LAN)",
            "Try another port/cable",
            "Restart computer",
        ]
    if category == Ticket.Category.SOFTWARE:
        return [
            "Restart application",
            "Update to latest version",
            "Reinstall if needed",
            "Capture screenshot of error",
        ]
    return []


def get_ai_user():
    """
    Create/get AI bot user for auto-response comments.
    """
    u, _ = User.objects.get_or_create(
        username="ai_bot",
        defaults={"email": "", "role": "ADMIN", "is_active": True},
    )
    if u.has_usable_password():
        u.set_unusable_password()
        u.save(update_fields=["password"])
    return u
