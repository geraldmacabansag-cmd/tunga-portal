"""The Services editor's server side, shared by:

  * the Office Representative  (office_dashboard/views.py → services, …)
  * the Super Admin            (admin_dashboard/views.py → admin_office_services, …)

Both use the same page (templates/office_dashboard/_service_editor_*.html)
and the same saving code below. The differences live in `Editor`:

                        Office Representative        Super Admin
  which office          their own office             the office picked on the page
  new services          "Pending Approval"           "Published" right away
  published services    locked (can't be edited)     can always be edited
  "editing off" switch  applies                      doesn't apply
"""
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (DownloadableForm, Notification, ProcessStep, Requirement,
                     Service, ServiceEditSettings)

LOCKED_MESSAGE = "This service is already published and can no longer be edited."


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

    def locked(self, service):
        return (not self.is_admin) and service.status == "published"

    def editing_enabled(self):
        return True if self.is_admin else ServiceEditSettings.get_solo().editing_enabled

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

    services_qs = all_services

    q = request.GET.get('q', '').strip()
    if q:
        services_qs = services_qs.filter(name__icontains=q)

    status = request.GET.get('status', '')
    if status:
        services_qs = services_qs.filter(status=status)

    services_qs = list(services_qs)
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

def add_service(request, ed, fallback_url):
    """fallback_url: where to go when the form didn't come from the Services
    page (the Office Profile page also has an "Add Service" button)."""
    next_page = request.POST.get('next') or request.GET.get('next')
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon') or 'fa-solid fa-file-signature'

        division = request.POST.get('division', '').strip() or ed.office.name
        classification = request.POST.get('classification', '').strip()
        transaction_types = request.POST.getlist('transaction_type')
        transaction_type = ",".join(transaction_types)
        who_may_avail = request.POST.get('who_may_avail', '').strip()
        service_scope = request.POST.get('service_scope', '').strip()
        if service_scope not in ('internal', 'external'):
            service_scope = ''

        if not name:
            messages.error(request, "Service name is required.")
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
        if not ed.editing_enabled():
            messages.error(request, "The Super Admin has turned off editing of services for all offices.")
            return redirect(ed.list_url(service.pk))

        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon') or service.icon

        division = request.POST.get('division', '').strip() or ed.office.name
        classification = request.POST.get('classification', '').strip()
        transaction_types = request.POST.getlist('transaction_type')
        transaction_type = ",".join(transaction_types)
        who_may_avail = request.POST.get('who_may_avail', '').strip()
        service_scope = request.POST.get('service_scope', '').strip()
        if service_scope not in ('internal', 'external'):
            service_scope = ''

        if not name:
            messages.error(request, "Service name is required.")
        else:
            service.name = name
            service.description = description
            service.icon = icon
            service.division = division
            service.classification = classification
            service.transaction_type = transaction_type
            service.who_may_avail = who_may_avail
            service.service_scope = service_scope
            service.save()
            messages.success(request, f'"{name}" was updated.')

    return redirect(ed.list_url(service.pk))


def delete_service(request, ed, pk):
    service = ed.service(pk)

    if request.method == "POST":
        name = service.name
        service.delete()
        messages.success(request, f'"{name}" was deleted.')
        if ed.is_admin:
            ed.tell_office("Service removed by the Super Admin",
                           f'The Super Admin deleted the service "{name}" from your office.')

    return redirect(ed.list_url())


def delete_service_form(request, ed, service_pk, pk):
    form = get_object_or_404(DownloadableForm, pk=pk, office=ed.office, service_id=service_pk)

    if request.method == "POST":
        title = form.title
        form.file.delete(save=False)
        form.delete()
        messages.success(request, f'"{title}" was deleted.')

    return redirect(ed.list_url(service_pk))


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

        service.steps.all().delete()

        fallback_order = 1
        created_any = False
        for i, title in enumerate(titles):
            title = title.strip()
            if not title:
                continue
            step_number_raw = step_numbers[i].strip() if i < len(step_numbers) else ""
            try:
                order = Decimal(step_number_raw) if step_number_raw else Decimal(fallback_order)
            except InvalidOperation:
                order = Decimal(fallback_order)
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
                processing_time=processing_time,
                person_responsible=person,
            )
            fallback_order += 1
            created_any = True

        if not created_any:
            messages.error(request, "Add at least one step with a name.")
        else:
            messages.success(request, "Client steps updated.")

    return redirect(ed.list_url(service.pk))


def save_reminders(request, ed, service_pk):
    service = ed.service(service_pk)

    if request.method == "POST":
        if ed.locked(service):
            return HttpResponse(LOCKED_MESSAGE, status=403)
        items_raw = request.POST.get('items', '')
        lines = [line.strip() for line in items_raw.splitlines() if line.strip()]
        service.reminders = "\n".join(lines)
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
                title=title,
                where_to_secure=where,
                transaction_type=transaction_type,
            )
            order += 1

        if order == 1:
            messages.error(request, "Add at least one requirement with a name.")
        else:
            messages.success(request, "Requirements updated.")

    return redirect(ed.list_url(service.pk))


def save_legal_basis(request, ed, service_pk):
    service = ed.service(service_pk)

    if request.method == "POST":
        if ed.locked(service):
            return HttpResponse(LOCKED_MESSAGE, status=403)
        service.legal_basis = request.POST.get('legal_basis', '').strip()
        service.save()

    return redirect(ed.list_url())


def save_schedule_of_service(request, ed, service_pk):
    service = ed.service(service_pk)

    if request.method == "POST":
        if ed.locked(service):
            return HttpResponse(LOCKED_MESSAGE, status=403)
        service.schedule_of_service = request.POST.get('schedule_of_service', '').strip()
        service.save()

    return redirect(ed.list_url())