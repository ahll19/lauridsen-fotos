"""
Delete the files of galleries that have passed their expiry date.

Run on a schedule by the app-cron container (architecture.md §6). The schedule itself
lives in .env as CRON_SCHEDULE_EXPIRE_GALLERIES — not in this file and not in the image.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from galleries.models import ClientGallery


class Command(BaseCommand):
    help = "Delete photographs belonging to expired client galleries, leaving a tombstone."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without touching anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()
        due = ClientGallery.objects.due_for_expiry(now)

        if not due.exists():
            self.stdout.write(f"[{now:%Y-%m-%d %H:%M}] No galleries due for expiry.")
            return

        for gallery in due:
            if dry_run:
                self.stdout.write(
                    f"Would expire '{gallery.label}' ({gallery.slug}), "
                    f"{gallery.photos.count()} photo(s), expired {gallery.expires_at:%Y-%m-%d}"
                )
                continue

            count = gallery.expire_now()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Expired '{gallery.label}' ({gallery.slug}): "
                    f"{count} photo(s) and all derivatives deleted from disk."
                )
            )
