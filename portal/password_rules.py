"""Password requirements for every account (sign up, forgot password,
change password — public site, Office Representative and Super Admin).

Added to settings.AUTH_PASSWORD_VALIDATORS, next to Django's own checks
(at least 8 characters, not too common, not all numbers, not too similar
to the name or email). The same list is shown under the password boxes.
"""
import re

from django.core.exceptions import ValidationError

RULES = [
    (r"[A-Z]", "Password must contain at least one uppercase letter."),
    (r"[a-z]", "Password must contain at least one lowercase letter."),
    (r"[0-9]", "Password must contain at least one number."),
    (r"[^A-Za-z0-9]", "Password must contain at least one special character (e.g. ! @ # $ %)."),
]


class StrongPasswordValidator:
    def validate(self, password, user=None):
        problems = [msg for pattern, msg in RULES if not re.search(pattern, password or "")]
        if problems:
            raise ValidationError(problems, code="password_too_weak")

    def get_help_text(self):
        return ("Your password must have an uppercase letter, a lowercase letter, "
                "a number and a special character.")