"""Copies each entry's comma-separated tags into the shared list. See 0003."""

from django.db import migrations


def text_to_tags(apps, schema_editor):
    TimelineEntry = apps.get_model("timeline", "TimelineEntry")
    Tag = apps.get_model("timeline", "Tag")
    for entry in TimelineEntry.objects.all():
        names = [" ".join(part.split()) for part in entry.tags.split(",")]
        for name in filter(None, names):
            # "Vinter" and "vinter" are one tag; the first spelling met is the one kept.
            tag = Tag.objects.filter(name__iexact=name).first() or Tag.objects.create(name=name)
            entry.tag_set.add(tag)


def tags_to_text(apps, schema_editor):
    TimelineEntry = apps.get_model("timeline", "TimelineEntry")
    for entry in TimelineEntry.objects.all():
        entry.tags = ", ".join(tag.name for tag in entry.tag_set.order_by("name"))[:200]
        entry.save(update_fields=["tags"])


class Migration(migrations.Migration):
    dependencies = [
        ("timeline", "0003_tag"),
    ]

    operations = [
        migrations.RunPython(text_to_tags, tags_to_text),
    ]
