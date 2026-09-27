from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import User
from auditlog.services import audit
from .models import KBArticle
from .forms import KBArticleForm


@login_required
def kb_list(request):
    qs = KBArticle.objects.filter(is_archived=False).order_by("-created_at")
    if request.user.role == User.Role.REQUESTER:
        qs = qs.filter(is_public=True)

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))

    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    return render(request, "knowledgebase/kb_list.html", {"page": page})


@login_required
def kb_detail(request, pk: int):
    a = get_object_or_404(KBArticle, pk=pk, is_archived=False)
    if not a.is_public and request.user.role == User.Role.REQUESTER:
        raise Http404()
    return render(request, "knowledgebase/kb_detail.html", {"a": a})


@login_required
def kb_create(request):
    if request.user.role not in {
        User.Role.TECHNICIAN,
        User.Role.MANAGER,
        User.Role.ADMIN,
    }:
        raise Http404()

    if request.method == "POST":
        form = KBArticleForm(request.POST)
        if form.is_valid():
            a = form.save(commit=False)
            a.created_by = request.user
            a.save()
            audit(request, "KB_CREATE", a, f"KB created {a.title}")
            return redirect("kb_detail", pk=a.pk)
    else:
        form = KBArticleForm()
    return render(request, "knowledgebase/kb_form.html", {"form": form})


@login_required
def kb_edit(request, pk: int):
    if request.user.role not in {
        User.Role.TECHNICIAN,
        User.Role.MANAGER,
        User.Role.ADMIN,
    }:
        raise Http404()

    article = get_object_or_404(KBArticle, pk=pk, is_archived=False)

    if request.method == "POST":
        form = KBArticleForm(request.POST, instance=article)
        if form.is_valid():
            article = form.save()
            audit(request, "KB_UPDATE", article, f"KB updated {article.title}")
            return redirect("kb_detail", pk=article.pk)
    else:
        form = KBArticleForm(instance=article)

    return render(
        request,
        "knowledgebase/kb_form.html",
        {"form": form, "article": article, "mode": "edit"},
    )


@login_required
def kb_archive(request, pk: int):
    if request.user.role not in {
        User.Role.TECHNICIAN,
        User.Role.MANAGER,
        User.Role.ADMIN,
    }:
        raise Http404()

    article = get_object_or_404(KBArticle, pk=pk, is_archived=False)

    if request.method != "POST":
        raise Http404()

    article.is_archived = True
    article.save(update_fields=["is_archived"])
    audit(request, "KB_ARCHIVE", article, f"KB archived {article.title}")
    return redirect("kb_list")
