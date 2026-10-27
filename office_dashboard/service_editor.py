"""The Services editor's server side, shared by:

  * the Office Representative  (office_dashboard/views.py → services, …)
  * the Super Admin            (admin_dashboard/views.py → admin_office_services, …)

Both use the same page (templates/office_dashboard/_service_editor_*.html)
and the same saving code below. The differences live in `Editor`:

                        Office Representative        Super Admin
  which office          their own office             the office picked on the page
  new services          "Pending Approval"           "Published" right away
  "Allow Service        ON: can add and edit         can always add and edit
   Editing" switch      everything (details,
  (Super Admin →        requirements, client steps,
   Services)            reminders, legal basis,
                        schedule, forms), published
                        services too.
                        OFF: view only, nothing can
                        be added or changed
  deleting a service    only while not yet published can always delete
                        (pending / returned); not
                        affected by the switch
"""
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (DownloadableForm, Notification, ProcessStep, Requirement,
                     Service, ServiceEditSettings)

LOCKED_MESSAGE = ("The Super Admin has turned off service editing for all offices. "
                  "Ask the Super Admin to turn it on if changes are needed.")


class Editor:
    def __init__(self, office, is_admin=False, admin_user=None):
        self.office = office
        self.is_admin = is_admin
        self.admin_user = admin_user
        self.ns = "admin_dashboard" if is_admin else "office_dashboard"

    # --- addresses -------------------------------------------------------
    def list_url(self, service_pk=None, tab=None):
        if self.is_admin:
            url = reverse("admin_dashboard:services", args=[self.office.pk])
        else:
            url = reverse("office_dashboard:services")
        params = []
        if service_pk:
            params.append(f"service={service_pk}")
        if tab:
            params.append(f"tab={tab}")
        return url + ("?" + "&".join(params) if params else "")

    def add_url(self):
        if self.is_admin:
            return reverse("admin_dashboard:add_service", args=[self.office.pk])
        return reverse("office_dashboard:add_service")

    def upload_url(self):
        if self.is_admin:
            return reverse("admin_dashboard:upload_form", args=[self.office.pk])
        return reverse("office_dashboard:upload_form")

    # --- rules -------------------------------------------------------------
    def service(self, pk):
        """A service of THIS office only (anything else = 404)."""
        return get_object_or_404(Service, pk=pk, office=self.office)

    def locked(self, service=None):
        """True when this person may not change services right now: an Office
        Representative while "Allow Service Editing" is off."""
        return not self.editing_enabled()

    def can_delete(self, service):
        """Office Representatives may delete a service only while it is not
        yet published (pending / returned) — the "Allow Service Editing"
        switch doesn't change this. The Super Admin can always delete."""
        return self.is_admin or service.status != "published"

    def editing_enabled(self):
        return True if self.is_admin else ServiceEditSettings.get_solo().editing_enabled

    def revised(self, service, save=False):
        """An Office Representative changed a pending / returned service:
        it goes (back) to "pending" and the Super Admin is told
        (notifications.resubmit). Nothing happens for the Super Admin's own edits."""
        if self.is_admin:
            return
        from .notifications import resubmit
        was_returned = service.status == "returned"
        resubmit(service)
        if save and getattr(service, "_rep_revised", False):
            service.save(update_fields=["status"])
        if was_returned:
            # its forms were returned with it: they go back for approval with it
            service.forms.filter(bundled_with_service=True, status="returned").update(status="pending")

    def tell_office(self, title, description):
        """Lets the office's representative know the Super Admin changed
        their services (shown in their Notifications)."""
        rep = getattr(self.office, "representative", None) if self.is_admin else None
        if rep is None:
            return
        try:
            Notification.objects.create(representative=rep, title=title[:255],
                                        description=description, level="info")
        except Exception:
            pass   # a notice must never stop the save


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------

def render_list(request, ed, template, extra=None):
    from .views import FORM_CATEGORY_CHOICES
    all_services = ed.office.services.all()

    total_count = all_services.count()
    published_count = all_services.filter(status='published').count()
    pending_count = all_services.filter(status='pending').count()
    returned_count = all_services.filter(status='returned').count()

    # every service goes to the page; search and status work in the browser
    # without reloading (static/js/list-filter.js)
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    services_qs = list(all_services)
    for service in services_qs:
        service.steps_json = json.dumps([
            {
                "step_number": str(step.order),
                "title": step.title,
                "agency_action": step.agency_action,
                "fee": step.fee,
                "processing_time": step.processing_time,
                "person_responsible": step.person_responsible,
            }
            for step in service.steps.all()
        ])
        service.requirements_json = json.dumps([
            {
                "title": r.title,
                "where_to_secure": r.where_to_secure,
                "transaction_type": r.transaction_type,
            }
            for r in service.requirements.all()
        ])

    context = {
        "services": services_qs,
        "editor_office": ed.office,
        "svc_ns": ed.ns,
        "svc_is_admin": ed.is_admin,
        "svc_add_url": ed.add_url(),
        "svc_upload_url": ed.upload_url(),
        "category_choices": Service.CATEGORY_CHOICES,
        "icon_choices": Service.ICON_CHOICES,
        "total_count": total_count,
        "published_count": published_count,
        "pending_count": pending_count,
        "returned_count": returned_count,
        "current_q": q,
        "current_status": status,
        "category_choices_forms": FORM_CATEGORY_CHOICES,
        "editing_globally_enabled": ed.editing_enabled(),
    }
    context.update(extra or {})
    return render(request, template, context)


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

VALID_ICONS = {value for value, _label in Service.ICON_CHOICES}


def _missing_fields(name, description, classification, transaction_types, who_may_avail):
    """The required fields of Add / Edit Service that are empty (the windows
    also check this in the browser before sending)."""
    checks = [("Service Name", name), ("Description", description), ("Classification", classification),
              ("Type of Transaction", transaction_types), ("Who May Avail", who_may_avail)]
    return [label for label, value in checks if not value]


def add_service(request, ed, fallback_url):
    """fallback_url: where to go when the form didn't come from the Services
    page (the Office Profile page also has an "Add Service" button)."""
    next_page = request.POST.get('next') or request.GET.get('next')
    if request.method == "POST" and ed.locked():
        messages.error(request, LOCKED_MESSAGE)
    elif request.method == "POST":
        name = request.POST.get('name', '').strip()[:150]
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon') or 'fa-solid fa-file-signature'
        if icon not in VALID_ICONS:
            icon = 'fa-solid fa-file-signature'

        division = (request.POST.get('division', '').strip() or ed.office.name)[:150]
        classification = request.POST.get('classification', '').strip()[:50]
        # only the three known types (the field holds at most 50 characters)
        transaction_types = [t for t in request.POST.getlist('transaction_type') if t in Service.TRANSACTION_TYPE_LABELS]
        transaction_type = ",".join(transaction_types)
        who_may_avail = request.POST.get('who_may_avail', '').strip()[:255]
        service_scope = request.POST.get('service_scope', '').strip()
        if service_scope not in ('internal', 'external'):
            service_scope = ''

        missing = _missing_fields(name, description, classification, transaction_types, who_may_avail)
        if missing:
            messages.error(request, "Please fill in: " + ", ".join(missing) + ".")
        else:
            extra = {}
            if ed.is_admin:
                # added by the Super Admin = already approved
                extra = {"status": "published", "approved_at": timezone.now()}
            service = Service.objects.create(
                office=ed.office,
                name=name,
                description=description,
                icon=icon,
                division=division,
                classification=classification,
                transaction_type=transaction_type,
                who_may_avail=who_may_avail,
                service_scope=service_scope,
                **extra,
            )
            if ed.is_admin:
                messages.success(request, f'"{name}" was added to {ed.office.name} and published. Add its requirements, client steps, fees and other details below.')
                ed.tell_office("New service added by the Super Admin",
                               f'The Super Admin added the service "{name}" to your office.')
            else:
                messages.success(request, f'"{name}" was added. Add its requirements, process steps, fees and other details below.')

            if next_page == 'services':
                # straight into the new service's details
                return redirect(ed.list_url(service.pk))
            return redirect(fallback_url)

    if next_page == 'services':
        return redirect(ed.list_url())
    return redirect(fallback_url)


def edit_service(request, ed, pk):
    service = ed.service(pk)

    if request.method == "POST":
        if ed.locked(service):
            messages.error(request, LOCKED_MESSAGE)
            return redirect(ed.list_url(service.pk))

        name = request.POST.get('name', '').strip()[:150]
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon') or service.icon
        if icon not in VALID_ICONS:
            icon = service.icon

        division = (request.POST.get('division', '').strip() or ed.office.name)[:150]
        classification = request.POST.get('classification', '').strip()[:50]
        # only the three known types (the field holds at most 50 characters)
        transaction_types = [t for t in request.POST.getlist('transaction_type') if t in Service.TRANSACTION_TYPE_LABELS]
        transaction_type = ",".join(transaction_types)
        who_may_avail = request.POST.get('who_may_avail', '').strip()[:255]
        service_scope = request.POST.get('service_scope', '').strip()
        if service_scope not in ('internal', 'external'):
            service_scope = ''

        missing = _missing_fields(name, description, classification, transaction_types, who_may_avail)
        if missing:
            messages.error(request, "Please fill in: " + ", ".join(missing) + ".")
        else:
            service.name = name
            service.description = description
            service.icon = icon
            service.division = division
            service.classification = classification
            service.transaction_type = transaction_type
            service.who_may_avail = who_may_avail
            service.service_scope = service_scope
            ed.revised(service)
            service.save()
            messages.success(request, f'"{name}" was updated.')

    return redirect(ed.list_url(service.pk))


def delete_service(request, ed, pk):
    service = ed.service(pk)

    if request.method == "POST" and not ed.can_delete(service):
        messages.error(request, f'"{service.name}" is already published and can no longer be deleted. '
                                "Ask the Super Admin if it should be removed.")
    elif request.method == "POST":
        name = service.name
        service.delete()
        messages.success(request, f'"{name}" was deleted.')
        if ed.is_admin:
            ed.tell_office("Service removed by the Super Admin",
                           f'The Super Admin deleted the service "{name}" from your office.')

    return redirect(ed.list_url())


def delete_service_form(request, ed, service_pk, pk):
    form = get_object_or_404(DownloadableForm, pk=pk, office=ed.office, service_id=service_pk)

    if request.method == "POST" and ed.locked():
        messages.error(request, LOCKED_MESSAGE)
    elif request.method == "POST":
        title = form.title
        form.file.delete(save=False)
        form.delete()
        messages.success(request, f'"{title}" was deleted.')

    return redirect(ed.list_url(service_pk))


def _step_number(raw, fallback):
    """The Client Step Number typed by the person (1, 1.1, 2.5 …). It is saved
    in a DecimalField(max_digits=6, decimal_places=2), so it must be a normal
    number from 0 to 9999.99 — anything else ("NaN", "1e9", "abc", 10000)
    becomes the step's position instead of crashing the save."""
    try:
        number = Decimal(raw) if raw else Decimal(fallback)
    except InvalidOperation:
        number = Decimal(fallback)
    if not number.is_finite() or number < 0 or number >= Decimal("10000"):
        number = Decimal(fallback) if Decimal(fallback) < 10000 else Decimal("9999")
    return number.quantize(Decimal("0.01"))


def save_process_steps(request, ed, service_pk):
    service = ed.service(service_pk)

    if request.method == "POST":
        if ed.locked(service):
            return HttpResponse(LOCKED_MESSAGE, status=403)

        step_numbers = request.POST.getlist('step_number[]')
        titles = request.POST.getlist('title[]')
        agency_actions = request.POST.getlist('agency[]')
        fees = request.POST.getlist('fee[]')
        processing_times = request.POST.getlist('processing_time[]')
        persons = request.POST.getlist('person[]')

        # Delete-and-recreate happens in ONE transaction: if anything goes
        # wrong (or no step has a name), the old steps are kept as they were.
        with transaction.atomic():
            service.steps.all().delete()

            fallback_order = 1
            created_any = False
            for i, title in enumerate(titles):
                title = title.strip()
                if not title:
                    continue
                step_number_raw = step_numbers[i].strip() if i < len(step_numbers) else ""
                order = _step_number(step_number_raw, fallback_order)
                agency_action = agency_actions[i].strip() if i < len(agency_actions) else ""
                fee = fees[i].strip() if i < len(fees) else ""
                processing_time = processing_times[i].strip() if i < len(processing_times) else ""
                person = persons[i].strip() if i < len(persons) else ""

                ProcessStep.objects.create(
                    service=service,
                    order=order,
                    title=title,
                    agency_action=agency_action,
                    fee=fee,
                    processing_time=processing_time[:150],
                    person_responsible=person[:150],
                )
                fallback_order += 1
                created_any = True

            if not created_any:
                transaction.set_rollback(True)   # keep the old steps

        if not created_any:
            messages.error(request, "Add at least one step with a name. Nothing was changed.")
        else:
            # Total Processing Time: typed by the office (not added up)
            service.processing_time = request.POST.get('total_processing_time', '').strip()[:100]
            service.save(update_fields=["processing_time"])
            messages.success(request, "Client steps updated.")
            ed.revised(service, save=True)

    return redirect(ed.list_url(service.pk))


def save_reminders(request, ed, service_pk):
    service = ed.service(service_pk)

    if request.method == "POST":
        if ed.locked(service):
            return HttpResponse(LOCKED_MESSAGE, status=403)
        items_raw = request.POST.get('items', '')
        lines = [line.strip() for line in items_raw.splitlines() if line.strip()]
        service.reminders = "\n".join(lines)
        ed.revised(service)
        service.save()

    return redirect(ed.list_url())


def save_requirements(request, ed, service_pk):
    service = ed.service(service_pk)

    if request.method == "POST":
        if ed.locked(service):
            return HttpResponse(LOCKED_MESSAGE, status=403)

        titles = request.POST.getlist('title[]')
        wheres = request.POST.getlist('where[]')
        txns = request.POST.getlist('txn[]')

        # One transaction: on any problem (or no named requirement) the old
        # requirements are kept as they were.
        with transaction.atomic():
            service.requirements.all().delete()

            order = 1
            for i, title in enumerate(titles):
                title = title.strip()
                if not title:
                    continue
                where = wheres[i].strip() if i < len(wheres) else ""
                transaction_type = txns[i].strip() if i < len(txns) else ""
                Requirement.objects.create(
                    service=service,
                    order=order,
                    title=title[:150],
                    where_to_secure=where[:200],
                    transaction_type=transaction_type[:100],
                )
                order += 1

            if order == 1:
                transaction.set_rollback(True)

        if order == 1:
            messages.error(request, "Add at least one requirement with a name. Nothing was changed.")
        else:
            messages.success(request, "Requirements updated.")
            ed.revised(service, save=True)

    return redirect(ed.list_url(service.pk))


def save_legal_basis(request, ed, service_pk):
    service = ed.service(service_pk)

    if request.method == "POST":
        if ed.locked(service):
            return HttpResponse(LOCKED_MESSAGE, status=403)
        service.legal_basis = request.POST.get('legal_basis', '').strip()
        ed.revised(service)
        service.save()

    return redirect(ed.list_url())


def save_schedule_of_service(request, ed, service_pk):
    service = ed.service(service_pk)

    if request.method == "POST":
        if ed.locked(service):
            return HttpResponse(LOCKED_MESSAGE, status=403)
        service.schedule_of_service = request.POST.get('schedule_of_service', '').strip()[:255]
        ed.revised(service)
        service.save()

    return redirect(ed.list_url())