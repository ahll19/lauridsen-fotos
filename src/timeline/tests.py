from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Tag, TimelineEntry


def entry(slug, *tags, visible=True):
    made = TimelineEntry.objects.create(
        slug=slug, title_da=slug, date=date(2026, 1, 1), visible=visible
    )
    made.tags.set(tags)
    return made


class TagTests(TestCase):
    def test_names_differing_only_in_case_are_one_tag(self):
        Tag.objects.create(name="Vinter")
        with self.assertRaises(ValidationError):
            Tag(name="vinter").full_clean()

    def test_spaces_are_tidied(self):
        self.assertEqual(Tag.objects.create(name="  blå   time ").name, "blå time")


class TimelineTagFilterTests(TestCase):
    def setUp(self):
        self.sea = Tag.objects.create(name="hav")
        self.seaside = Tag.objects.create(name="havn")
        self.hidden = Tag.objects.create(name="skjult")
        entry("ved-havet", self.sea)
        entry("i-havnen", self.seaside)
        entry("kladde", self.hidden, visible=False)

    def test_filter_matches_the_whole_tag_in_any_case(self):
        """Free text matched "hav" inside "havn"; a tag matches only itself."""
        response = self.client.get(reverse("timeline:index"), {"tag": "HAV"})
        self.assertEqual([e.slug for e in response.context["entries"]], ["ved-havet"])

    def test_only_tags_on_published_entries_are_offered(self):
        response = self.client.get(reverse("timeline:index"))
        self.assertEqual(response.context["tags"], ["hav", "havn"])

    def test_entry_page_links_its_tags(self):
        response = self.client.get(reverse("timeline:entry", args=["ved-havet"]))
        self.assertContains(response, "?tag=hav")


class TagMergeTests(TestCase):
    def test_merge_keeps_the_most_used_tag_and_moves_every_entry(self):
        owner = User.objects.create_superuser("owner", "o@example.com", "pw-for-tests-only")
        self.client.force_login(owner)
        winter = Tag.objects.create(name="vinter")
        typo = Tag.objects.create(name="vintre")
        first = entry("en", winter)
        entry("to", winter)
        third = entry("tre", typo)

        self.client.post(
            reverse("admin:timeline_tag_changelist"),
            {"action": "merge_tags", "_selected_action": [winter.pk, typo.pk]},
        )

        self.assertEqual(list(Tag.objects.values_list("name", flat=True)), ["vinter"])
        self.assertEqual(third.tag_list(), ["vinter"])
        self.assertEqual(first.tag_list(), ["vinter"])


class TimelineStandsAloneTests(TestCase):
    def test_timeline_does_not_point_into_the_portfolio(self):
        """The timeline is grouped by tags only (ADR 0016)."""
        entry("lysmalerier")
        response = self.client.get(reverse("timeline:index"))
        self.assertNotContains(response, "entry__related")
        self.assertFalse(hasattr(TimelineEntry, "related_category"))
