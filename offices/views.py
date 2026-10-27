from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.contrib import messages
from django.http import FileResponse, JsonResponse, HttpResponse
from .pdf_serve import pdf_response
from office_dashboard.form_fields import field_to_dict, to_json
from office_dashboard.gallery_items import photo_items, content_items
from django.urls import reverse
from django.db.models import F
from .models import Office
from office_dashboard.models import (
    Announcement, DownloadableForm, NewsUpdate, Photo, Service,
    FormField, FormSubmission, FormSubmissionValue,
    OrgChartNode, OrgChartSettings,
)
import re
import io

def serve_form_pdf(request, pk):
    """Original PDF of a published form (View / Download links and the
    pdf.js preview in Fill Out Online)."""
    form_obj = get_object_or_404(DownloadableForm, pk=pk, status="published")
    # The PDF file itself (View / Download) needs an account, like Fill Out
    # Online. Anyone may still look at the form in our own viewer page
    # (view_form), which gets the pages as ?as=json for pdf.js.
    # After logging in, the visitor comes back to the form's page.
    as_json = request.GET.get("as") == "json"
    download = request.GET.get("download") == "1"
    if not as_json and not request.user.is_authenticated:
        messages.info(request, "Please log in or create an account to download this form.")
        return redirect_to_login(reverse("offices:view_form", args=[pk]))
    if download:
        # Downloads by citizens (the Download buttons) — shown to the office
        # and the Super Admin as "Total Downloads".
        DownloadableForm.objects.filter(pk=pk).update(download_count=F("download_count") + 1)
    return pdf_response(
        request, form_obj.file,
        filename=_pdf_filename(form_obj.title, ""),
        as_attachment=download,
    )

def _pdf_filename(title, suffix="_filled"):
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", (title or "").strip()).strip("_") or "form"
    return f"{safe_title}{suffix}.pdf"


def view_form(request, pk):
    """Our own PDF viewer page. It draws the form with pdf.js on a canvas
    instead of relying on the visitor's browser to display a PDF — Android
    Chrome, many in-app browsers and some older phones can't show a PDF
    inline and just fail or force a download."""
    form_obj = get_object_or_404(DownloadableForm, pk=pk, status="published")
    return render(request, "offices/form-view.html", {
        "form_obj": form_obj,
        "office": form_obj.office,
        "can_fill_online": form_obj.fields.exists(),
    })


def _parse_leading_number(text):
    """Pulls a leading numeric value off a free-text processing-time string
    (e.g. "5 minutes" -> 5.0)."""
    if not text:
        return None
    match = re.match(r"\s*(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def _compute_total_processing_time(steps):
    """Sums any steps whose processing time starts with a number, and
    appends the free-text ones (e.g. "Same day") as-is."""
    total = 0
    has_numeric = False
    text_parts = []
    for step in steps:
        n = _parse_leading_number(step.processing_time)
        if n is not None:
            total += n
            has_numeric = True
        elif step.processing_time:
            text_parts.append(step.processing_time)
    parts = []
    if has_numeric:
        parts.append(str(int(total)) if total == int(total) else f"{total:.2f}")
    parts.extend(text_parts)
    return " + ".join(parts) if parts else "—"


def _group_requirements_for_charter(requirements):
    """Requirements with no type of transaction come first as a plain list,
    then the rest are grouped under their type of transaction (alphabetically) —
    same grouping used in the office rep's and Super Admin's Citizen's Charter views."""
    general = [r for r in requirements if not r.transaction_type]
    grouped = {}
    for r in requirements:
        if r.transaction_type:
            grouped.setdefault(r.transaction_type, []).append(r)
    grouped_list = [(key, grouped[key]) for key in sorted(grouped.keys())]
    return general, grouped_list


def office_detail(request, slug):
    office = get_object_or_404(
        Office.objects.exclude(slug="lgu-super-admin"),
        slug=slug,
        is_visible=True,
    )
    rep = getattr(office, "representative", None)

    services = list(
        Service.objects.filter(office=office, status="published")
        .prefetch_related("requirements", "steps", "fees", "forms", "forms__fields")
        .order_by("order", "name")
    )

    # Pre-compute each service's "Citizen's Charter" data (same shape the
    # office rep's Preview modal and the Super Admin's service page use) so
    # the floating modal on this page can render it directly, no JS needed.
    for s in services:
        steps = list(s.steps.all())
        requirements = list(s.requirements.all())
        general_requirements, grouped_requirements = _group_requirements_for_charter(requirements)
        s.charter_steps = steps
        s.charter_total_processing_time = s.processing_time or "—"   # typed by the office
        s.charter_general_requirements = general_requirements
        s.charter_grouped_requirements = grouped_requirements
        s.charter_has_requirements = bool(requirements)
        # Only forms that have been approved and published: the PDF links below
        # (offices:view_pdf) 404 for anything still pending, returned, rejected
        # or archived. The forms are already prefetched, so filter in Python.
        s.charter_forms = sorted(
            (f for f in s.forms.all() if f.status == "published"),
            key=lambda f: f.date_uploaded,
            reverse=True,
        )
        # A form can be filled out online only once the office has placed
        # fields on it (prefetched above, so no extra queries here).
        for f in s.charter_forms:
            f.can_fill_online = len(f.fields.all()) > 0

    announcements = (
        Announcement.public().filter(representative=rep)
        .order_by("-date_posted", "-last_updated", "-created_at")[:3]
        if rep else []
    )

    forms = (
        DownloadableForm.objects.filter(office=office, status="published")
        .order_by("-date_uploaded")[:6]
    )

    # This office's latest published news, for the "News and Updates" panel.
    news_items = list(
        NewsUpdate.objects.filter(representative=rep, status="published")
        .order_by("-date_published", "-last_updated", "-created_at")[:3]
    ) if rep else []
    for n in news_items:
        n.display_date = n.date_published or n.created_at.date()

    # Every published photo from this office, newest first. The template shows
    # the first four in the Gallery panel and reveals the rest when the visitor
    # clicks "View more images about this office".
    # Gallery panel: this office's published photos plus the images of its
    # published announcements, news and events — newest first.
    photos = []
    if rep:
        photos = list(photo_items(Photo.objects.filter(representative=rep, status="published")))
        photos += list(content_items(representative=rep))
        photos.sort(key=lambda i: i["created"], reverse=True)

    # The office's Organizational Chart, shown at the bottom of the page once
    # the rep clicked "Show on office page" in the chart builder.
    org_nodes = []
    if OrgChartSettings.objects.filter(office=office, show_on_office_page=True).exists():
        org_nodes = list(OrgChartNode.objects.filter(office=office).order_by("order", "id"))

    return render(request, "offices/office_detail.html", {
        "office": office,
        "org_nodes": org_nodes,
        "rep": rep,
        "services": services,
        "announcements": announcements,
        "forms": forms,
        "news_items": news_items,
        "photos": photos,
    })

def _prefill_value_for_field(field, user):
    """Best-effort prefill for text fields whose label suggests a name or
    email, using the logged-in citizen's account. Anything else is left
    blank for the person to fill in themselves."""
    if field.field_type != "text":
        return ""
    label = (field.label or "").lower()
    if "email" in label:
        return user.email or ""
    if "name" in label and "business" not in label and "office" not in label:
        return user.get_full_name() or user.username
    return ""


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


@login_required
def fill_form(request, pk):
    form_obj = get_object_or_404(DownloadableForm, pk=pk, status="published")
    fields = list(form_obj.fields.all().order_by("page_number", "order", "id"))

    if not fields:
        if _is_ajax(request):
            return JsonResponse({"error": "This form isn't set up for online filling yet. You can still download the original PDF."}, status=400)
        messages.error(request, "This form isn't set up for online filling yet. You can still download the original PDF.")
        return redirect("offices:office_detail", slug=form_obj.office.slug)

    for f in fields:
        f.initial_value = _prefill_value_for_field(f, request.user)

    pages = sorted(set(f.page_number for f in fields))

    # Position + text style of every field (same data the builder saves).
    fields_json = to_json([dict(field_to_dict(f), initial_value=f.initial_value) for f in fields])

    template = "offices/_form_fill_fragment.html" if _is_ajax(request) else "offices/form-fill.html"

    return render(request, template, {
        "form_obj": form_obj,
        "office": form_obj.office,
        "fields": fields,
        "pages": pages,
        "fields_json": fields_json,
    })


ANSWER_MAX_LENGTH = 500   # = FormSubmissionValue.value max_length


@login_required
def submit_form(request, pk):
    form_obj = get_object_or_404(DownloadableForm, pk=pk, status="published")
    fields = list(form_obj.fields.all().order_by("page_number", "order", "id"))

    if request.method != "POST" or not fields:
        return redirect("offices:fill_form", pk=pk)

    values_by_field = {}
    missing_labels = []
    too_long_labels = []

    for f in fields:
        if f.field_type == "checkbox":
            value = "Yes" if request.POST.get(f"field_{f.id}") == "on" else ""
        else:
            value = request.POST.get(f"field_{f.id}", "").strip()
            if f.required and not value:
                missing_labels.append(f.label)
            # FormSubmissionValue.value holds at most 500 characters (the
            # live PostgreSQL database refuses anything longer).
            if len(value) > ANSWER_MAX_LENGTH:
                too_long_labels.append(f.label)
        values_by_field[f.id] = value

    if missing_labels or too_long_labels:
        parts = []
        if missing_labels:
            parts.append("Please fill in: " + ", ".join(missing_labels) + ".")
        if too_long_labels:
            parts.append(f"These answers are longer than {ANSWER_MAX_LENGTH} characters, please shorten them: "
                         + ", ".join(too_long_labels) + ".")
        error_text = " ".join(parts)
        if _is_ajax(request):
            return JsonResponse({"error": error_text}, status=400)
        messages.error(request, error_text)
        return redirect("offices:fill_form", pk=pk)

    submission = FormSubmission.objects.create(form=form_obj, user=request.user)
    FormSubmissionValue.objects.bulk_create([
        FormSubmissionValue(submission=submission, field=f, value=values_by_field.get(f.id, ""))
        for f in fields
    ])

    download_url = reverse("offices:download_filled", args=[submission.pk])

    # Tell the office: it appears in Office Dashboard → Submissions.
    _notify_office_of_submission(submission)

    # The page's script asks for JSON and then points the browser at the
    # download URL. That is a plain, native file download (the same as
    # tapping a Download link), so the phone saves it straight into its
    # Downloads folder — unlike a JavaScript "blob" download, which several
    # mobile and in-app browsers silently drop.
    if _is_ajax(request):
        return JsonResponse({
            "ok": True,
            "download_url": download_url,
            "filename": _pdf_filename(form_obj.title),
            "reference_no": submission.reference_no,
            "office": form_obj.office.name if form_obj.office else "",
        })

    messages.success(request, f"Your form was sent to {form_obj.office.name if form_obj.office else 'the office'}. "
                              f"Reference no. {submission.reference_no}. Follow its status in My Account.")
    return redirect(download_url)


def _notify_office_of_submission(submission):
    """Dashboard notification for the office's representative."""
    try:
        from office_dashboard.models import OfficeRepresentative
        from office_dashboard.notifications import notify
        rep = OfficeRepresentative.objects.filter(office=submission.form.office).first()
        who = submission.user.get_full_name() or submission.user.email
        notify(rep, "submissions", f"New online submission: {submission.form.title}",
               f"{who} · {submission.reference_no}", level="info",
               link_url=reverse("office_dashboard:submissions") + "?status=submitted")
    except Exception:
        pass   # never block the citizen's submission


@login_required
def download_filled(request, pk):
    """Sends the person's own saved answers, written onto the office's PDF,
    as a file download. Only the citizen who filled it in can fetch it."""
    # The citizen's own copy stays available even if the office later
    # archives the form, so they can always get what they sent.
    submission = get_object_or_404(
        FormSubmission.objects.select_related("form", "form__office"),
        pk=pk, user=request.user,
    )
    form_obj = submission.form

    values_by_field = {
        v.field_id: v.value
        for v in submission.values.all()
    }
    # all_objects: also fields taken off the form later, so old answers still show
    fields = list(FormField.all_objects.filter(form=form_obj).order_by("page_number", "order", "id"))

    try:
        pdf_bytes = _stamp_pdf(form_obj, fields, values_by_field)
    except Exception:
        import traceback
        traceback.print_exc()
        return HttpResponse(
            "Your responses were saved, but the filled PDF couldn't be generated. "
            "Please go back and try again, or contact the office.",
            status=500,
            content_type="text/plain",
        )

    response = FileResponse(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        filename=_pdf_filename(form_obj.title),
        content_type="application/pdf",
    )
    response["Content-Length"] = str(len(pdf_bytes))
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _stamp_pdf(form_obj, fields, values_by_field):
    """Writes the citizen's answers onto a copy of the office's original PDF
    at the positions the office representative placed each field (see
    offices/pdf_stamp.py — the text is part of the page, not an annotation,
    so every PDF viewer, including phone ones, shows it)."""
    from .pdf_stamp import stamp_pdf

    form_obj.file.open("rb")
    try:
        source_bytes = form_obj.file.read()
    finally:
        form_obj.file.close()

    return stamp_pdf(source_bytes, fields, values_by_field)