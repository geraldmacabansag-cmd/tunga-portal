"""GET /healthz/ -> "ok". DigitalOcean (and uptime monitors) open this address
to check the website is running. It answers before any other check, so it
works even when the server asks with its own internal address."""
from django.db import connection
from django.http import HttpResponse


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/healthz/":
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT 1")
            except Exception:
                return HttpResponse("database error", status=503, content_type="text/plain")
            return HttpResponse("ok", content_type="text/plain")
        return self.get_response(request)