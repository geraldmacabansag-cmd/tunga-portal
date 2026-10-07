import base64

from django.http import HttpResponse, JsonResponse


def read_pdf_bytes(file_field):
    """Reads the whole PDF from storage (local disk or Cloudinary)."""
    file_field.open("rb")
    try:
        return file_field.read()
    finally:
        file_field.close()


def pdf_response(request, file_field, filename="form.pdf", as_attachment=False):
    """One response used by every PDF endpoint.

    ?as=json  -> {"pdf": "<base64>"}  (used by static/js/tunga-pdf.js for
                 the pdf.js previews; JSON is never hijacked by download
                 manager extensions or Chrome's "download PDFs" setting)
    otherwise -> the real PDF file (for View / Download links).
    """
    try:
        data = read_pdf_bytes(file_field)
    except Exception as e:
        msg = "Could not load the PDF from storage: %s" % e
        if request.GET.get("as") == "json":
            return JsonResponse({"error": msg}, status=500)
        return HttpResponse(msg, status=500, content_type="text/plain")

    if not data.startswith(b"%PDF"):
        msg = "The stored file is not a valid PDF. Please upload it again."
        if request.GET.get("as") == "json":
            return JsonResponse({"error": msg}, status=500)
        return HttpResponse(msg, status=500, content_type="text/plain")

    if request.GET.get("as") == "json":
        response = JsonResponse({"pdf": base64.b64encode(data).decode("ascii")})
    else:
        response = HttpResponse(data, content_type="application/pdf")
        kind = "attachment" if as_attachment else "inline"
        response["Content-Disposition"] = '%s; filename="%s"' % (kind, filename)
        response["Content-Length"] = str(len(data))

    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response