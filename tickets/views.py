from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import SLAConfig
from .forms import SLAConfigForm
from accounts.models import User
from auditlog.services import audit
from notifications.services import notify_ticket_event
from .models import Ticket, TicketAttachment, TicketComment
from .forms import TicketCreateForm, TicketAssignForm, TicketStatusForm, CommentForm
from .services import mark_first_response_if_needed, mark_resolved_fields_if_needed
from aiassist.services import classify_text, auto_response_steps, get_ai_user
from django.core.exceptions import ValidationError
from django.db import transaction


def _can_view_ticket(user, ticket: Ticket) -> bool:
    if user.is_superuser or getattr(user, "role", None) == User.Role.ADMIN:
        return True
    if user.role == User.Role.MANAGER:
        return True
    if user.role == User.Role.TECHNICIAN:
        return ticket.assigned_to_id == user.id or ticket.assigned_to_id is None
    return ticket.requester_id == user.id


@login_required
def helpdesk_search(request):
    """Search visible tickets (including archived for managers/admins) and KB solutions."""
    from knowledgebase.models import KBArticle

    q = request.GET.get("q", "").strip()
    ticket_results = Ticket.objects.none()
    kb_results = KBArticle.objects.none()

    if q:
        tickets = Ticket.objects.all()
        if not request.user.is_manager():
            tickets = tickets.filter(is_archived=False)
            if request.user.role == User.Role.REQUESTER:
                tickets = tickets.filter(requester=request.user)
            elif request.user.role == User.Role.TECHNICIAN:
                tickets = tickets.filter(Q(assigned_to=request.user) | Q(assigned_to__isnull=True))

        ticket_results = tickets.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(id__icontains=q)
        ).select_related("requester", "assigned_to").order_by("-created_at")[:20]

        kb_results = KBArticle.objects.filter(
            is_archived=False
        ).filter(Q(title__icontains=q) | Q(body__icontains=q))
        if request.user.role == User.Role.REQUESTER:
            kb_results = kb_results.filter(is_public=True)
        kb_results = kb_results.order_by("-created_at")[:20]

    return render(
        request,
        "search/results.html",
        {"q": q, "ticket_results": ticket_results, "kb_results": kb_results},
    )


@login_required
def ticket_list(request):
    qs = Ticket.objects.filter(is_archived=False).order_by("-created_at")

    u = request.user
    if u.role == User.Role.REQUESTER:
        qs = qs.filter(requester=u)
    elif u.role == User.Role.TECHNICIAN:
        qs = qs.filter(Q(assigned_to=u) | Q(assigned_to__isnull=True))

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()
    priority = request.GET.get("priority", "").strip()

    if q:
        qs = qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(id__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category=category)
    if priority:
        qs = qs.filter(priority=priority)

    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "tickets/ticket_list.html", {"page": page, "Ticket": Ticket})


@login_required
def ticket_assign(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk, is_archived=False)
    if not request.user.is_manager():
        raise Http404()

    if request.method != "POST":
        raise Http404()

    form = TicketAssignForm(request.POST, instance=ticket)
    if form.is_valid():
        form.save()
        audit(request, "TICKET_ASSIGN", ticket, f"Assigned to {ticket.assigned_to}")
        notify_ticket_event(ticket, event="assigned")
        messages.success(request, "Assigned successfully.")
    else:
        messages.error(request, "Invalid assignment.")

    return redirect("ticket_detail", pk=ticket.pk)


@login_required
def ticket_detail(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk, is_archived=False)
    if not _can_view_ticket(request.user, ticket):
        raise Http404()

    assign_form = None
    status_form = None
    if request.user.is_manager():
        assign_form = TicketAssignForm(instance=ticket)
    if request.user.role in {User.Role.TECHNICIAN, User.Role.MANAGER, User.Role.ADMIN}:
        status_form = TicketStatusForm(instance=ticket)

    comment_form = CommentForm()

    # Filter comments: requester can't see internal notes
    comments = ticket.comments.order_by("created_at")
    if request.user.role == User.Role.REQUESTER:
        comments = comments.filter(is_internal=False)

    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "assign_form": assign_form,
            "status_form": status_form,
            "comment_form": comment_form,
            "comments": comments,
        },
    )


@login_required
def ticket_create(request):
    if request.method == "POST":
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            files = request.FILES.getlist("attachments")
            try:
                # Validate every attachment before committing the ticket.
                for uploaded in files:
                    TicketAttachment._meta.get_field("file").run_validators(uploaded)

                with transaction.atomic():
                    ticket = form.save(commit=False)
                    ticket.requester = request.user

                    cat, pri, conf, _debug = classify_text(
                        ticket.title + "\n" + ticket.description
                    )
                    ticket.ai_category = cat
                    ticket.ai_priority = pri
                    ticket.ai_confidence = conf

                    if ticket.category == Ticket.Category.OTHER:
                        ticket.category = cat
                    if ticket.priority == Ticket.Priority.MEDIUM:
                        ticket.priority = pri

                    ticket.save()

                    for uploaded in files:
                        TicketAttachment.objects.create(
                            ticket=ticket, file=uploaded, uploaded_by=request.user
                        )

                    steps = auto_response_steps(ticket.category)
                    if steps:
                        ai_user = get_ai_user()
                        TicketComment.objects.create(
                            ticket=ticket,
                            author=ai_user,
                            message="AI Auto-response (suggested steps):\n"
                            + "\n".join([f"- {step}" for step in steps]),
                            is_internal=False,
                        )

                    audit(
                        request,
                        action="TICKET_CREATE",
                        obj=ticket,
                        message=f"Created {ticket.display_id()}",
                    )
                    notify_ticket_event(ticket, event="created")

                messages.success(request, f"Ticket created: {ticket.display_id()}")
                return redirect("ticket_detail", pk=ticket.pk)
            except ValidationError as exc:
                form.add_error(None, str(exc))
            except Exception:
                # Keep user-facing errors generic; the detailed exception is logged by Django.
                import logging
                logging.getLogger(__name__).exception("Ticket creation failed")
                form.add_error(None, "The ticket could not be created. Please try again.")

        messages.error(request, "Please correct the errors.")
    else:
        form = TicketCreateForm()

    return render(request, "tickets/ticket_create.html", {"form": form})


@login_required
def ticket_update_status(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk, is_archived=False)

    if request.user.role not in {
        User.Role.TECHNICIAN,
        User.Role.MANAGER,
        User.Role.ADMIN,
    }:
        raise Http404()
    if request.user.role == User.Role.TECHNICIAN and ticket.assigned_to_id not in {None, request.user.id}:
        raise Http404()

    form = TicketStatusForm(request.POST, instance=ticket)

    if request.method == "POST" and form.is_valid():
        try:
            updated = form.save(commit=False)
            updated.full_clean()  # enforce Ticket.clean() rules
            updated.save()
            mark_resolved_fields_if_needed(updated)

            audit(request, "TICKET_STATUS", updated, f"Status -> {updated.status}")
            notify_ticket_event(updated, event="status_changed")
            messages.success(request, "Status updated.")
            return redirect("ticket_detail", pk=updated.pk)

        except ValidationError as e:
            messages.error(request, f"Status update failed: {e}")

    # If invalid, re-render detail page with form errors
    assign_form = (
        TicketAssignForm(instance=ticket) if request.user.is_manager() else None
    )
    comment_form = CommentForm()

    comments = ticket.comments.order_by("created_at")
    if request.user.role == User.Role.REQUESTER:
        comments = comments.filter(is_internal=False)

    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "assign_form": assign_form,
            "status_form": form,  # keep errors
            "comment_form": comment_form,
            "comments": comments,
        },
    )


@login_required
def ticket_add_comment(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk, is_archived=False)
    if not _can_view_ticket(request.user, ticket):
        raise Http404()

    form = CommentForm(request.POST)
    if form.is_valid():
        c = form.save(commit=False)
        c.ticket = ticket
        c.author = request.user

        # requester cannot create internal notes
        if request.user.role == User.Role.REQUESTER:
            c.is_internal = False

        c.save()
        mark_first_response_if_needed(c)
        audit(request, "TICKET_COMMENT", ticket, "Comment added")
        notify_ticket_event(ticket, event="comment_added")
        messages.success(request, "Comment posted.")
    else:
        messages.error(request, "Comment invalid.")
    return redirect("ticket_detail", pk=ticket.pk)


@login_required
def attachment_download(request, attachment_id: int):
    att = get_object_or_404(TicketAttachment, pk=attachment_id)
    if not _can_view_ticket(request.user, att.ticket):
        raise Http404()
    return FileResponse(
        att.file.open("rb"), as_attachment=True, filename=att.file.name.split("/")[-1]
    )


@login_required
def sla_list(request):
    if not request.user.is_manager():
        raise Http404()
    qs = SLAConfig.objects.order_by("priority")
    return render(request, "tickets/sla_list.html", {"qs": qs})


@login_required
def sla_edit(request, pk: int):
    if not request.user.is_manager():
        raise Http404()
    obj = get_object_or_404(SLAConfig, pk=pk)
    if request.method == "POST":
        form = SLAConfigForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "SLA updated.")
            return redirect("sla_list")
    else:
        form = SLAConfigForm(instance=obj)
    return render(request, "tickets/sla_form.html", {"form": form, "obj": obj})


@login_required
def ticket_archive(request, pk: int):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_manager():
        raise Http404()
    ticket.is_archived = True
    ticket.save(update_fields=["is_archived"])
    audit(request, "TICKET_ARCHIVE", ticket, "Archived ticket")
    messages.success(request, "Ticket archived.")
    return redirect("ticket_list")


@login_required
def ticket_archived_list(request):
    if not request.user.is_manager():
        raise Http404()
    qs = Ticket.objects.filter(is_archived=True).order_by("-updated_at")
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    return render(request, "tickets/ticket_archived_list.html", {"page": page})
