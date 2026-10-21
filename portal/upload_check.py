"""Checks every uploaded file by its CONTENT, not just its name.

A file named "photo.jpg" must really be a picture, "form.pdf" must really be
a PDF, and a ".zip" (backups) or ".docx"/".xlsx" must really be that kind of
file. Anything else that pretends (for example a program renamed to .jpg)
is refused before any page saves it, and so is every other kind of file
(only pictures, PDFs and .zip/.docx/.xlsx/.pptx files are accepted).

Pictures in vector (.svg) or web-page (.html, .js…) formats are refused
because they can carry hidden scripts.

Added to settings.MIDDLEWARE as "portal.upload_check.UploadCheckMiddleware",
so it covers every upload form on the site at once.
"""
import zipfile

from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme

IMAGE_EXTS = {"jpg", "jpeg", "jfif", "png", "gif", "webp", "bmp", "ico", "tif", "tiff", "avif"}
PDF_EXTS = {"pdf"}
ZIP_EXTS = {"zip", "docx", "xlsx", "pptx"}
ALLOWED_EXTS = IMAGE_EXTS | PDF_EXTS | ZIP_EXTS
BLOCKED_EXTS = {"svg", "svgz", "html", "htm", "xhtml", "js", "mjs", "php", "exe", "bat", "cmd",
                "sh", "msi", "com", "scr", "jar", "py", "vbs", "ps1", "dll"}


def _ext(name):
    return name.rsplit(".", 1)[-1].lower() if "." in (name or "") else ""


def _is_image(f):
    from PIL import Image
    try:
        f.seek(0)
        with Image.open(f) as img:
            img.verify()          # reads the whole picture structure
        return True
    except Exception:
        return False
    finally:
        f.seek(0)


def _is_pdf(f):
    try:
        f.seek(0)
        if b"%PDF-" not in f.read(1024):
            return False
        f.seek(0)
        from pypdf import PdfReader
        PdfReader(f, strict=False)   # can it actually be opened as a PDF?
        return True
    except Exception:
        return False
    finally:
        f.seek(0)


def _is_zip(f):
    try:
        f.seek(0)
        return zipfile.is_zipfile(f)
    except Exception:
        return False
    finally:
        f.seek(0)


def problem_with(f):
    """None when the file is what its name says, otherwise the reason."""
    ext = _ext(f.name)
    if ext in BLOCKED_EXTS:
        return f"“{f.name}” can't be uploaded: .{ext} files are not allowed for security reasons."
    if ext in IMAGE_EXTS and not _is_image(f):
        return f"“{f.name}” is not a real picture (or it is damaged). Please upload a JPG or PNG image."
    if ext in PDF_EXTS and not _is_pdf(f):
        return f"“{f.name}” is not a real PDF file (or it is damaged). Please upload a valid PDF."
    if ext in ZIP_EXTS and not _is_zip(f):
        return f"“{f.name}” is not a valid .{ext} file (or it is damaged)."
    if ext not in ALLOWED_EXTS:
        # Only the kinds of files the portal actually uses are accepted
        # (an allow-list: anything not on it is refused, even if it's new).
        kind = f".{ext} files" if ext else "Files without an extension"
        return (f"“{f.name}” can't be uploaded: {kind} are not accepted. "
                "Please upload a picture (JPG, PNG, WEBP), a PDF or a backup .zip.")
    content_type = (getattr(f, "content_type", "") or "").lower()
    if content_type.startswith("image/") and ext not in IMAGE_EXTS and not _is_image(f):
        return f"“{f.name}” is not a supported picture. Please upload a JPG or PNG image."
    return None


class UploadCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.content_type == "multipart/form-data":
            for _field, files in request.FILES.lists():
                for f in files:
                    error = problem_with(f)
                    if error:
                        return self.refuse(request, error)
        return self.get_response(request)

    @staticmethod
    def refuse(request, error):
        wants_json = (request.headers.get("X-Requested-With") == "XMLHttpRequest"
                      or "application/json" in request.headers.get("Accept", ""))
        if wants_json:
            return JsonResponse({"success": False, "ok": False, "error": error, "errors": [error]}, status=400)
        messages.error(request, error)
        back = request.META.get("HTTP_REFERER") or ""
        if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
            back = request.path
        return HttpResponseRedirect(back)