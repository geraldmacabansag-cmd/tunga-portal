"""Online form submissions: what happens after a citizen clicks Submit on
"Fill Out Online".

  Citizen submits  ->  the office sees it in Office Dashboard → Submissions
  Office updates the status (Received / Processing / Ready for pickup /
  Declined) and can add a note  ->  the citizen sees it in My Account →
  My Form Submissions, gets a notification on the website and an email.

The Super Admin sees every office's submissions (Super Admin → Submissions).
Used by office_dashboard/views.py, admin_dashboard/views.py and portal.
"""
import io
import threading

from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone

from .models import FormSubmission

# status -> how it looks everywhere (badge colour, icon, text for the citizen)
STATUS_INFO = {
    "submitted": {"label": "Submitted", "badge": "badge-blue", "icon": "fa-solid fa-paper-plane",
                  "citizen": "Sent to the office. Waiting for the office to receive it."},
    "received": {"label": "Received", "badge": "badge-blue", "icon": "fa-solid fa-inbox",
                 "citizen": "The office has received your form."},
    "processing": {"label": "Processing", "badge": "badge-amber", "icon": "fa-solid fa-gears",
                   "citizen": "The office is working on your request."},
    "ready": {"label": "Ready for pickup", "badge": "badge-green", "icon": "fa-solid fa-circle-check",
              "citizen": "Your request is ready. You may get it at the office."},
    "declined": {"label": "Declined", "badge": "badge-red", "icon": "fa-solid fa-circle-xmark",
                 "citizen": "The office could not process your request. See the note from the office."},
}

# statuses the office can choose (it can't go back to "Submitted")
OFFICE_CHOICES = [(k, v["label"]) for k, v in STATUS_INFO.items() if k != "submitted"]

# Only these statuses are emailed, because the citizen has to do something
# (come to the office, or fix the form). Received / Processing are shown on
# the website only (My Account + the bell), to save the daily email limit.
EMAIL_STATUSES = ("ready", "declined")

# The citizen can rate the service (1–5 + comment) once the request is finished.
FEEDBACK_STATUSES = ("ready", "declined")


def decorate(submissions):
    """Adds to each submission for the templates: .info (STATUS_INFO entry),
    .fb (its SubmissionFeedback or None) and .can_rate."""
    for s in submissions:
        s.info = STATUS_INFO.get(s.status, STATUS_INFO["submitted"])
        try:
            s.fb = s.feedback
        except Exception:
            s.fb = None
        s.can_rate = s.fb is None and s.status in FEEDBACK_STATUSES
    return submissions


def base_queryset():
    return (FormSubmission.objects
            .select_related("form", "form__office", "user", "user__profile", "feedback")
            .order_by("-submitted_at"))


def apply_filters(qs, request):
    """?q= (name, email, form, reference no.), ?status=, ?form=, ?office="""
    q = (request.GET.get("q") or "").strip()
    if q:
        cond = (Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
                | Q(user__email__icontains=q) | Q(form__title__icontains=q))
        # "TNG-2026-00012" or "12" finds submission #12
        digits = q.rsplit("-", 1)[-1]
        if digits.isdigit():
            cond |= Q(pk=int(digits))
        qs = qs.filter(cond)
    status = request.GET.get("status") or ""
    if status == "open":
        qs = qs.filter(status__in=["submitted", "received", "processing"])
    elif status in STATUS_INFO:
        qs = qs.filter(status=status)
    form_id = request.GET.get("form") or ""
    if form_id.isdigit():
        qs = qs.filter(form_id=int(form_id))
    office_id = request.GET.get("office") or ""
    if office_id.isdigit():
        qs = qs.filter(form__office_id=int(office_id))
    return qs, {"q": q, "status": status, "form": form_id, "office": office_id}


def counts(qs):
    """Numbers for the stat cards (on the unfiltered list)."""
    c = {k: 0 for k in STATUS_INFO}
    for status in qs.values_list("status", flat=True):
        c[status] = c.get(status, 0) + 1
    c["total"] = sum(c[k] for k in STATUS_INFO)
    c["in_progress"] = c["received"] + c["processing"]
    return c


def filled_pdf_response(submission, download=False):
    """The citizen's answers written on the office's PDF (same as the copy
    the citizen downloaded). Inline for viewing, or as a download."""
    from offices.views import _stamp_pdf, _pdf_filename
    form_obj = submission.form
    values = {v.field_id: v.value for v in submission.values.all()}
    # all_objects: also fields taken off the form later, so old answers still show
    from .models import FormField
    fields = list(FormField.all_objects.filter(form=form_obj).order_by("page_number", "order", "id"))
    try:
        data = _stamp_pdf(form_obj, fields, values)
    except Exception:
        return HttpResponse("The filled PDF couldn't be generated (the office's original PDF may be missing).",
                            status=500, content_type="text/plain")
    name = (submission.user.get_full_name() or submission.user.username).replace(" ", "_")
    response = FileResponse(io.BytesIO(data), as_attachment=download,
                            filename=_pdf_filename(f"{form_obj.title}_{name}_{submission.reference_no}", ""),
                            content_type="application/pdf")
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def update_status(submission, new_status, note, changed_by):
    """Saves the new status / note. Returns True if something changed.
    The website notification is automatic for every status (see
    admin_dashboard/context_processors.public_notifications); an email is
    sent only for Ready for pickup and Declined (EMAIL_STATUSES)."""
    if new_status not in STATUS_INFO or new_status == "submitted":
        return False
    note = (note or "").strip()[:1000]
    if new_status == submission.status and note == submission.office_note:
        return False
    submission.status = new_status
    submission.office_note = note
    submission.status_updated_at = timezone.now()
    submission.status_updated_by = changed_by[:150]
    submission.save(update_fields=["status", "office_note", "status_updated_at", "status_updated_by"])
    if new_status in EMAIL_STATUSES:
        send_status_email(submission)
    return True


def send_status_email(submission):
    """Emails the citizen about the new status, in the background so the
    office's page doesn't wait for the email service. Does nothing if the
    email provider isn't set up (Super Admin → System Settings)."""
    to = submission.user.email
    if not to:
        return
    info = STATUS_INFO[submission.status]
    office = submission.form.office.name if submission.form.office else "the municipality"
    name = submission.user.first_name or "there"
    subject = f"{submission.form.title}: {info['label']} ({submission.reference_no})"
    note = submission.office_note
    plain = (f"Hi {name},\n\n"
             f"Your online form \"{submission.form.title}\" (reference no. {submission.reference_no}) "
             f"sent to {office} is now: {info['label']}.\n{info['citizen']}\n"
             + (f"\nNote from the office:\n{note}\n" if note else "")
             + "\nYou can also see this in My Account → My Form Submissions on the Tunga Portal,"
               " where you can also rate the service. Your rating helps us serve you better.\n")
    from django.utils.html import escape
    html = (f'<div style="font-family:sans-serif;max-width:520px;">'
            f'<p>Hi {escape(name)},</p>'
            f'<p>Your online form <b>{escape(submission.form.title)}</b> '
            f'(reference no. <b>{submission.reference_no}</b>) sent to {escape(office)} is now:</p>'
            f'<p style="font-size:20px;font-weight:700;margin:14px 0;">{escape(info["label"])}</p>'
            f'<p style="color:#555;">{escape(info["citizen"])}</p>'
            + (f'<div style="background:#f3f6fb;border-radius:8px;padding:12px 14px;margin:14px 0;">'
               f'<b>Note from the office:</b><br>{escape(note).replace(chr(10), "<br>")}</div>' if note else "")
            + '<p style="color:#888;font-size:13px;">You can also see this in My Account → My Form Submissions on the Tunga Portal, '
              'where you can also <b>rate the service</b>. Your rating helps us serve you better.</p></div>')

    def _send():
        try:
            from admin_dashboard.email_utils import send_via_configured_provider
            send_via_configured_provider(subject, plain, html, to)
        except Exception:
            pass   # the website notification still shows the new status

    threading.Thread(target=_send, daemon=True).start()


# ---------------------------------------------------------------------------
# Client satisfaction (Anti-Red Tape Act, RA 11032)
# ---------------------------------------------------------------------------
def satisfaction(feedback_qs):
    """{count, average, satisfied_pct, stars: {5: n, 4: n, ...}} for a set of
    SubmissionFeedback. "Satisfied" = rated 4 or 5."""
    ratings = list(feedback_qs.values_list("rating", flat=True))
    n = len(ratings)
    stars = {k: ratings.count(k) for k in (5, 4, 3, 2, 1)}
    return {
        "count": n,
        "average": round(sum(ratings) / n, 2) if n else None,
        "satisfied_pct": round(100 * (stars[5] + stars[4]) / n) if n else None,
        "stars": stars,
        "bars": [{"stars": k, "count": stars[k], "pct": round(100 * stars[k] / n) if n else 0} for k in (5, 4, 3, 2, 1)],
    }


def satisfaction_by_office():
    """One row per office that has ratings, best average first."""
    from offices.models import Office
    from .models import SubmissionFeedback
    rows = []
    for office in Office.objects.filter(downloadable_forms__submissions__feedback__isnull=False).distinct():
        s = satisfaction(SubmissionFeedback.objects.filter(submission__form__office=office))
        s["office"] = office
        rows.append(s)
    rows.sort(key=lambda r: (-(r["average"] or 0), -r["count"]))
    return rows


def save_feedback(submission, rating, comment):
    """Validates and saves the citizen's rating. Returns (feedback, error)."""
    from .models import SubmissionFeedback
    if submission.status not in FEEDBACK_STATUSES:
        return None, "You can rate this service once your request is finished."
    if SubmissionFeedback.objects.filter(submission=submission).exists():
        return None, "You already rated this service. Thank you!"
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        rating = 0
    if rating < 1 or rating > 5:
        return None, "Please choose from 1 to 5 stars."
    fb = SubmissionFeedback.objects.create(submission=submission, rating=rating,
                                           comment=(comment or "").strip()[:1000])
    _notify_office_of_feedback(fb)
    from admin_dashboard.alerts import low_rating
    low_rating(fb)   # 1–2 stars: the Super Admin is told too
    return fb, None


def _notify_office_of_feedback(fb):
    try:
        from django.urls import reverse
        from .models import OfficeRepresentative
        from .notifications import notify
        s = fb.submission
        rep = OfficeRepresentative.objects.filter(office=s.form.office).first()
        notify(rep, "feedback", f"New rating: {fb.rating}/5 for {s.form.title}",
               (f"{s.reference_no} · {fb.comment[:120]}" if fb.comment else s.reference_no),
               level="success" if fb.rating >= 4 else ("warning" if fb.rating == 3 else "danger"),
               link_url=reverse("office_dashboard:submissions") + f"?q={s.reference_no}")
    except Exception:
        pass