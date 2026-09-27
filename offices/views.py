from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, JsonResponse, Http404, HttpResponse
from .models import Office
from office_dashboard.models import (
    Announcement, DownloadableForm, Photo, Service,
    FormField, FormSubmission, FormSubmissionValue,
)
import re
import io
import json

@login_required
def mayor(request):
    return render(request, 'offices/mayorsoffice.html')


def serve_form_pdf(request, pk):
    """Streams a published form's original PDF through our own server instead
    of linking straight to the storage backend's public URL. Some storage
    providers (Cloudinary in particular) block unsigned/direct access to
    PDF and ZIP files by default and return a 401 — opening the file through
    Django's storage API (as this does) uses authenticated access instead,
    so it works regardless of that setting. Used for the "View/Open Original
    PDF" links, the plain Download button, and as the source pdf.js loads
    for the online fill-out popup."""
    form_obj = get_object_or_404(DownloadableForm, pk=pk, status="published")

    try:
        form_obj.file.open("rb")
        data = form_obj.file.read()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(
            "Could not load the PDF from storage: %s: %s" % (type(e).__name__, e),
            status=500,
            content_type="text/plain",
        )
    finally:
        try:
            form_obj.file.close()
        except Exception:
            pass

    filename = form_obj.file.name.rsplit("/", 1)[-1]
    as_attachment = request.GET.get("download") == "1"

    return FileResponse(
        io.BytesIO(data),
        as_attachment=as_attachment,
        filename=filename,
        content_type="application/pdf",
    )


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
        .prefetch_related("requirements", "steps", "fees", "forms")
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
        s.charter_total_processing_time = _compute_total_processing_time(steps)
        s.charter_general_requirements = general_requirements
        s.charter_grouped_requirements = grouped_requirements
        s.charter_has_requirements = bool(requirements)
        s.charter_forms = s.forms.all().order_by('-date_uploaded')

    announcements = (
        Announcement.objects.filter(representative=rep, status="published")
        .order_by("-date_posted", "-created_at")[:5]
        if rep else []
    )

    forms = (
        DownloadableForm.objects.filter(office=office, status="published")
        .order_by("-date_uploaded")[:6]
    )

    photos = (
        Photo.objects.filter(representative=rep, status="published")
        .order_by("-created_at")[:4]
        if rep else []
    )

    return render(request, "offices/office_detail.html", {
        "office": office,
        "rep": rep,
        "services": services,
        "announcements": announcements,
        "forms": forms,
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

    fields_json = json.dumps([
        {
            "id": f.id,
            "label": f.label,
            "field_type": f.field_type,
            "required": f.required,
            "page_number": f.page_number,
            "x": f.x,
            "y": f.y,
            "width": f.width,
            "height": f.height,
            "initial_value": f.initial_value,
        }
        for f in fields
    ])

    template = "offices/_form_fill_fragment.html" if _is_ajax(request) else "offices/form-fill.html"

    return render(request, template, {
        "form_obj": form_obj,
        "office": form_obj.office,
        "fields": fields,
        "pages": pages,
        "fields_json": fields_json,
    })


@login_required
def submit_form(request, pk):
    form_obj = get_object_or_404(DownloadableForm, pk=pk, status="published")
    fields = list(form_obj.fields.all().order_by("page_number", "order", "id"))

    if request.method != "POST" or not fields:
        return redirect("offices:fill_form", pk=pk)

    values_by_field = {}
    missing_labels = []

    for f in fields:
        if f.field_type == "checkbox":
            value = "Yes" if request.POST.get(f"field_{f.id}") == "on" else ""
        else:
            value = request.POST.get(f"field_{f.id}", "").strip()
            if f.required and not value:
                missing_labels.append(f.label)
        values_by_field[f.id] = value

    if missing_labels:
        error_text = "Please fill in: " + ", ".join(missing_labels)
        if _is_ajax(request):
            return JsonResponse({"error": error_text}, status=400)
        messages.error(request, error_text)
        return redirect("offices:fill_form", pk=pk)

    submission = FormSubmission.objects.create(form=form_obj, user=request.user)
    FormSubmissionValue.objects.bulk_create([
        FormSubmissionValue(submission=submission, field=f, value=values_by_field.get(f.id, ""))
        for f in fields
    ])

    try:
        pdf_bytes = _stamp_pdf(form_obj, fields, values_by_field)
    except Exception:
        import traceback
        traceback.print_exc()
        error_text = "Your responses were saved, but the filled PDF couldn't be generated. Please try downloading again or contact the office."
        if _is_ajax(request):
            return JsonResponse({"error": error_text}, status=500)
        messages.error(request, error_text)
        return redirect("offices:fill_form", pk=pk)

    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", form_obj.title.strip()) or "form"
    filename = f"{safe_title}_filled.pdf"

    return FileResponse(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )


def _stamp_pdf(form_obj, fields, values_by_field):
    """Stamps the citizen's typed answers directly onto a copy of the
    office's original PDF, at the exact positions the office representative
    placed each field in the form builder (x/y/width/height are fractions
    of the page size, with y measured from the top)."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.annotations import FreeText

    form_obj.file.open("rb")
    try:
        source_bytes = form_obj.file.read()
    finally:
        form_obj.file.close()

    reader = PdfReader(io.BytesIO(source_bytes))
    writer = PdfWriter()
    writer.append(reader)

    fields_by_page = {}
    for f in fields:
        fields_by_page.setdefault(f.page_number, []).append(f)

    for page_number, page_fields in fields_by_page.items():
        page_index = page_number - 1
        if page_index < 0 or page_index >= len(writer.pages):
            continue

        page = writer.pages[page_index]
        mediabox = page.mediabox
        page_width = float(mediabox.width)
        page_height = float(mediabox.height)

        for f in page_fields:
            value = values_by_field.get(f.id, "")
            text = "X" if f.field_type == "checkbox" else value
            if not text:
                continue

            x0 = f.x * page_width
            x1 = (f.x + f.width) * page_width
            y1 = page_height * (1 - f.y)
            y0 = page_height * (1 - f.y - f.height)
            if x1 <= x0:
                x1 = x0 + 10
            if y1 <= y0:
                y1 = y0 + 10

            font_size = max(8, min(14, (y1 - y0) * 0.65))

            annotation = FreeText(
                text=str(text),
                rect=(x0, y0, x1, y1),
                font="Helvetica",
                font_size=f"{font_size:.0f}pt",
                font_color="000000",
                border_color=None,
                background_color=None,
            )
            writer.add_annotation(page_number=page_index, annotation=annotation)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()