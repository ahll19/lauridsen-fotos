"""
Tests for the design preview (ROADMAP 0.2.0).

The preview is temporary, but while it exists it must be impossible for it to reach
visitors — a half-finished visual direction appearing on the live site would be worse than
having no preview at all. These tests go when the preview does.
"""

from django.test import TestCase, override_settings


@override_settings(DESIGN_PREVIEW_ENABLED=True)
class DesignPreviewEnabledTests(TestCase):
    def test_comparison_page_lists_every_variation(self):
        response = self.client.get("/design/")
        self.assertEqual(response.status_code, 200)
        for name in ["Atelier", "Atelier Sage", "Atelier Slate", "Atelier Press"]:
            self.assertContains(response, name)

    def test_each_variation_changes_exactly_one_axis(self):
        """
        The point of the comparison: Sage and Slate reuse the original's fonts, and Press
        reuses its colours. If a variation started moving two axes, a preference between
        them would stop meaning anything.
        """
        from core import themes

        sage = themes.get("atelier-sage")
        slate = themes.get("atelier-slate")
        press = themes.get("atelier-press")
        original = themes.DEFAULT

        # Colour-only variations must not pull in a different typeface.
        self.assertIsNone(sage.fonts)
        self.assertIsNone(slate.fonts)

        # The typography variation must keep the original palette.
        self.assertEqual(press.swatches, original.swatches)

        # ...and the colour variations must actually differ in colour.
        self.assertNotEqual(sage.swatches, original.swatches)
        self.assertNotEqual(slate.swatches, original.swatches)

    def test_comparison_page_is_not_indexable(self):
        self.assertContains(self.client.get("/design/"), "noindex")

    def test_baseline_loads_no_extra_stylesheet(self):
        """Atelier is site.css itself, so choosing it must add nothing."""
        response = self.client.get("/")
        self.assertNotContains(response, "css/themes/")

    def test_choosing_a_direction_applies_it_everywhere(self):
        self.client.post("/design/choose/", {"theme": "atelier-slate", "next": "/"})

        for url in ["/", "/portfolio/", "/timeline/", "/priser/", "/kontakt/"]:
            with self.subTest(page=url):
                self.assertContains(self.client.get(url), "css/themes/atelier-slate.css")

    def test_switcher_is_shown(self):
        self.assertContains(self.client.get("/"), "design-switcher")

    def test_unknown_direction_falls_back_to_the_baseline(self):
        response = self.client.post("/design/choose/", {"theme": "nonsense", "next": "/"})
        self.assertEqual(response.status_code, 302)
        self.assertNotContains(self.client.get("/"), "css/themes/")

    def test_redirect_target_must_be_local(self):
        response = self.client.post(
            "/design/choose/", {"theme": "atelier-sage", "next": "https://evil.example/"}
        )
        self.assertEqual(response["Location"], "/")

    def test_protocol_relative_redirect_is_refused(self):
        response = self.client.post(
            "/design/choose/", {"theme": "atelier-sage", "next": "//evil.example/"}
        )
        self.assertEqual(response["Location"], "/")

    def test_choosing_returns_to_the_page_you_were_on(self):
        response = self.client.post(
            "/design/choose/", {"theme": "atelier-sage", "next": "/timeline/?tag=vinter"}
        )
        self.assertEqual(response["Location"], "/timeline/?tag=vinter")


@override_settings(DESIGN_PREVIEW_ENABLED=False)
class DesignPreviewDisabledTests(TestCase):
    """How production runs: the preview must be completely inert."""

    def test_comparison_page_is_gone(self):
        self.assertEqual(self.client.get("/design/").status_code, 404)

    def test_choosing_is_gone(self):
        self.assertEqual(
            self.client.post("/design/choose/", {"theme": "atelier-slate"}).status_code, 404
        )

    def test_no_switcher_on_the_site(self):
        self.assertNotContains(self.client.get("/"), "design-switcher")

    def test_a_stale_cookie_cannot_change_the_site(self):
        """Someone who previewed a direction must not keep seeing it once this is off."""
        self.client.cookies["design_theme"] = "atelier-slate"
        self.assertNotContains(self.client.get("/"), "css/themes/")
