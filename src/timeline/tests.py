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
        Tag.objects.create(name_da="Vinter")
        with self.assertRaises(ValidationError):
            Tag(name_da="vinter").full_clean()

    def test_spaces_are_tidied(self):
        self.assertEqual(Tag.objects.create(name_da="  blå   time ").name_da, "blå time")


class TimelineTagFilterTests(TestCase):
    def setUp(self):
        self.sea = Tag.objects.create(name_da="hav")
        self.seaside = Tag.objects.create(name_da="havn")
        self.hidden = Tag.objects.create(name_da="skjult")
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
        winter = Tag.objects.create(name_da="vinter")
        typo = Tag.objects.create(name_da="vintre")
        first = entry("en", winter)
        entry("to", winter)
        third = entry("tre", typo)

        self.client.post(
            reverse("admin:timeline_tag_changelist"),
            {"action": "merge_tags", "_selected_action": [winter.pk, typo.pk]},
        )

        self.assertEqual(list(Tag.objects.values_list("name_da", flat=True)), ["vinter"])
        self.assertEqual(third.tag_list(), ["vinter"])
        self.assertEqual(first.tag_list(), ["vinter"])


class TimelineStandsAloneTests(TestCase):
    def test_timeline_does_not_point_into_the_portfolio(self):
        """The timeline is grouped by tags only (ADR 0016)."""
        entry("lysmalerier")
        response = self.client.get(reverse("timeline:index"))
        self.assertNotContains(response, "entry__related")
        self.assertFalse(hasattr(TimelineEntry, "related_category"))


class TagLanguageTests(TestCase):
    def setUp(self):
        self.winter = Tag.objects.create(name_da="vinter", name_en="winter")
        self.fog = Tag.objects.create(name_da="tåge")
        entry("frost", self.winter)
        entry("dis", self.fog)

    def get(self, language, **params):
        from django.utils import translation

        with translation.override(language):
            url = reverse("timeline:index")
        return self.client.get(url, params)

    def test_each_language_shows_its_own_name(self):
        self.assertEqual(self.get("da").context["tags"], ["tåge", "vinter"])
        self.assertEqual(self.get("en").context["tags"], ["tåge", "winter"])

    def test_english_falls_back_to_danish(self):
        self.assertIn("tåge", self.get("en").context["tags"])

    def test_a_filtered_link_survives_switching_language(self):
        """?tag=vinter on the English page finds the tag and shows it as "winter"."""
        response = self.get("en", tag="vinter")
        self.assertEqual([e.slug for e in response.context["entries"]], ["frost"])
        self.assertEqual(response.context["active_tag"], "winter")

    def test_an_unknown_tag_shows_nothing(self):
        self.assertEqual(list(self.get("da", tag="sommer").context["entries"]), [])

    def test_english_names_are_unique_too_but_may_be_empty(self):
        Tag.objects.create(name_da="sne")
        Tag.objects.create(name_da="is", name_en="")
        with self.assertRaises(ValidationError):
            Tag(name_da="frost", name_en="Winter").full_clean()
