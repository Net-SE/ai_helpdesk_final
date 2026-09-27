import base64
from django.contrib.auth import authenticate
from django.http import JsonResponse


def basic_authenticate(request):
    """Authenticate a request using HTTP Basic Authentication."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError, base64.binascii.Error):
        return None
    return authenticate(request, username=username, password=password)


def require_auth(request):
    user = basic_authenticate(request)
    if not user or not user.is_active:
        response = JsonResponse({"detail": "Authentication credentials were not provided or are invalid."}, status=401)
        response["WWW-Authenticate"] = 'Basic realm="IT Assist API"'
        return None, response
    return user, None
