"""
Tags become a shared list (Tag) instead of free text on each entry.

Three steps, so that no entry loses a tag: the list and a new relation are added here,
0004 copies every entry's comma-separated tags into them, and 0005 removes the old text
field and gives the relation its name. Reversing runs the same steps backwards and writes
the tags back as text.
"""

import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("timeline", "0002_timelineentryphoto_alt_text_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=60, verbose_name="name")),
            ],
            options={
                "verbose_name": "tag",
                "verbose_name_plural": "tags",
                "ordering": [django.db.models.functions.text.Lower("name")],
                "constraints": [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower("name"),
                        name="unique_tag_name_ignoring_case",
                        violation_error_message="A tag with this name already exists.",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="timelineentry",
            name="tag_set",
            field=models.ManyToManyField(
                blank=True, related_name="+", to="timeline.tag", verbose_name="tags"
            ),
        ),
    ]
