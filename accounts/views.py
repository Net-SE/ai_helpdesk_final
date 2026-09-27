from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django_ratelimit.decorators import ratelimit

from .forms import StyledAuthenticationForm


@login_required
def me(request):
    u = request.user
    return JsonResponse({"username": u.username, "role": getattr(u, "role", None)})


@ratelimit(key="ip", rate="10/m", block=True)
def login_view(request):
    if request.user.is_authenticated:
        return redirect("ticket_list")

    form = StyledAuthenticationForm(request, data=request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            login(request, form.get_user())
            return redirect("ticket_list")
        messages.error(request, "Invalid username or password.")

    return render(request, "registration/login.html", {"form": form})
