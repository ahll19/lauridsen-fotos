"""
Send a deliberate error report, to prove the owner would hear about a real one.

An unhandled exception is mailed to the owner through the relay, which is the whole of
the application-error monitoring (architecture.md §9). That is easy to assume and hard to
notice the absence of: a relay that refuses the sender, or a wrong OWNER_EMAIL, fails
silently until the day it matters. This raises an exception and logs it exactly the way
Django logs one that escaped a view, so what arrives is what a real failure would send.

    scripts/dev.sh manage test_error_report
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a deliberate error report to the owner, through the real mail path."

    def handle(self, *args, **options):
        if settings.DEBUG:
            raise CommandError(
                "Error reports are only mailed with DJANGO_DEBUG=0, so there is nothing to "
                "test here. Run this on the server, or under scripts/prodcheck.sh --keep."
            )

        try:
            raise RuntimeError("Deliberate test error from manage.py test_error_report")
        except RuntimeError:
            # The same logger, level and extras Django uses for an unhandled exception.
            logging.getLogger("django.request").error(
                "Internal Server Error: /deliberate-test-error/",
                exc_info=True,
                extra={"status_code": 500, "request": None},
            )

        self.stdout.write(
            f"Sent to {settings.OWNER_EMAIL} via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}. "
            "Check that it arrived — a relay accepting a message is not the same thing."
        )
