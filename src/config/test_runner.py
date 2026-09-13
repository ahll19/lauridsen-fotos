"""
A test runner that gives the suite its own data directory.

The gallery tests create real photographs on disk and then exercise the code that deletes
them — `expire_now()` calls `shutil.rmtree()` on a directory derived from the gallery slug.
Pointed at the live `DATA_ROOT`, as they were, that is a destructive operation running
against the same tree that holds real client photographs, separated from them only by the
slugs happening not to collide.

Django replaces the database for a test run but says nothing about the filesystem, so the
isolation has to be arranged here. Every test writes into a temporary directory that is
removed when the run finishes.
"""

import shutil
import tempfile
from pathlib import Path

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class IsolatedDataRunner(DiscoverRunner):
    """DiscoverRunner with DATA_ROOT, MEDIA_ROOT and the thumbnail cache redirected."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)

        self._data_root = Path(tempfile.mkdtemp(prefix="lauridsen-fotos-tests-"))
        media = self._data_root / "media"
        thumbnails = self._data_root / "cache" / "thumbnails"
        for directory in (media, thumbnails):
            directory.mkdir(parents=True, exist_ok=True)

        self._overrides = override_settings(
            DATA_ROOT=self._data_root,
            MEDIA_ROOT=media,
            THUMBNAIL_MEDIA_ROOT=thumbnails,
        )
        self._overrides.enable()

    def teardown_test_environment(self, **kwargs):
        self._overrides.disable()
        shutil.rmtree(self._data_root, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
