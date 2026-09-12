"""
Remove tombstone rows once they have outlived their usefulness.

A tombstone exists so a client returning late sees "no longer available" instead of a
404. After GALLERY_TOMBSTONE_RETENTION_DAYS past expiry that message has done its job and
the row goes too, so nothing lingers indefinitely.
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from galleries.models import ClientGallery


class Command(BaseCommand):
    help = "Permanently delete tombstoned galleries past the retention window."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        now = timezone.now()
        due = ClientGallery.objects.due_for_purge(now)
        days = settings.GALLERY_TOMBSTONE_RETENTION_DAYS

        if not due.exists():
            self.stdout.write(f"[{now:%Y-%m-%d %H:%M}] No tombstones older than {days} days.")
            return

        for gallery in due:
            if options["dry_run"]:
                self.stdout.write(f"Would purge '{gallery.label}' ({gallery.slug})")
                continue
            label, slug = gallery.label, gallery.slug
            gallery.delete()
            self.stdout.write(self.style.SUCCESS(f"Purged '{label}' ({slug})."))
