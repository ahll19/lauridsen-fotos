"""
Tag names in Danish and English. Each existing name becomes the Danish one; English starts
empty, and the English site shows the Danish name until it is filled in.
"""

import django.db.models.functions.text
from django.db import migrations, models


def name_to_danish(apps, schema_editor):
    Tag = apps.get_model("timeline", "Tag")
    for tag in Tag.objects.all():
        tag.name_da = tag.name
        tag.save(update_fields=["name_da"])


def danish_to_name(apps, schema_editor):
    Tag = apps.get_model("timeline", "Tag")
    for tag in Tag.objects.all():
        tag.name = tag.name_da or tag.name
        tag.save(update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [
        ('timeline', '0007_remove_related_category'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tag',
            options={'ordering': [django.db.models.functions.text.Lower('name_da')], 'verbose_name': 'tag', 'verbose_name_plural': 'tags'},
        ),
        migrations.RemoveConstraint(
            model_name='tag',
            name='unique_tag_name_ignoring_case',
        ),
        migrations.AddField(
            model_name='tag',
            name='name_da',
            field=models.CharField(max_length=60, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='tag',
            name='name_en',
            field=models.CharField(max_length=60, null=True, verbose_name='name'),
        ),
        migrations.RunPython(name_to_danish, danish_to_name),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('name_da'), name='unique_tag_name_da_ignoring_case', violation_error_message='A tag with this name already exists.'),
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('name_en'), condition=models.Q(('name_en__isnull', False), models.Q(('name_en', ''), _negated=True)), name='unique_tag_name_en_ignoring_case', violation_error_message='A tag with this English name already exists.'),
        ),
    ]
