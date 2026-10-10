import pytest


@pytest.fixture(autouse=True)
def isolated_map_snapshots(settings, tmp_path):
    """Tests must not overwrite or expose snapshots in the development map cache."""
    settings.CACHES = {
        **settings.CACHES,
        "maps": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": str(tmp_path / "test-maps"),
        },
    }
