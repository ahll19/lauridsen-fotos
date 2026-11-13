"""Removes the old text field and names the relation `tags`. See 0003."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("timeline", "0004_copy_tags"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="timelineentry",
            name="tags",
        ),
        migrations.RenameField(
            model_name="timelineentry",
            old_name="tag_set",
            new_name="tags",
        ),
        migrations.AlterField(
            model_name="timelineentry",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                help_text="Choose from the tags already used; the + adds a new one.",
                related_name="entries",
                to="timeline.tag",
                verbose_name="tags",
            ),
        ),
    ]
