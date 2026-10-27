"""python manage.py delete_expired_accounts

Deletes the citizen accounts whose 30 days after "Delete my account" are
over (portal/account_deletion.py). The website also does this by itself at
most once an hour, so this is only needed as an extra daily job."""
from django.core.management.base import BaseCommand

from portal.account_deletion import purge_due


class Command(BaseCommand):
    help = "Delete the accounts whose 30-day deletion period is over."

    def handle(self, *args, **opts):
        n = purge_due()
        self.stdout.write(f"Deleted {n} account(s).")