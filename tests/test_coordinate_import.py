import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from routing.models import DatasetState, Station
from tests.test_importing import import_csv, row, source

pytestmark = pytest.mark.django_db


def artifact(tmp_path, record):
    path = tmp_path / "coordinates.json"
    path.write_text(json.dumps([record]))
    return path


def record(station):
    return {
        "opis_id": station.opis_id,
        "location_fingerprint": station.location_fingerprint,
        "latitude": 32.4,
        "longitude": -104.2,
        "policy": "unit-test",
        "identity_verified": True,
        "source": "unit test only",
        "evidence": "Synthetic fixture inside isolated test database",
    }


def test_reviewed_coordinate_import_and_resume(tmp_path):
    import_csv(source(tmp_path, [row()]))
    item = Station.objects.get()
    path = artifact(tmp_path, record(item))
    call_command("import_station_coordinates", str(path), reviewed=True)
    revision = DatasetState.objects.get().revision
    item.refresh_from_db()
    assert item.latitude == 32.4 and item.enrichment_status == "accepted"
    call_command("import_station_coordinates", str(path), reviewed=True)
    assert DatasetState.objects.get().revision == revision


@pytest.mark.parametrize(
    "change",
    [
        {"identity_verified": False},
        {"synthetic": True},
        {"location_fingerprint": "bad"},
        {"latitude": 91},
        {"opis_id": 99},
    ],
)
def test_coordinate_rejection(tmp_path, change):
    import_csv(source(tmp_path, [row()]))
    item = Station.objects.get()
    with pytest.raises(CommandError):
        call_command(
            "import_station_coordinates",
            str(artifact(tmp_path, {**record(item), **change})),
            reviewed=True,
        )
    assert Station.objects.get().latitude is None


def test_explicit_review_gate(tmp_path):
    with pytest.raises(CommandError, match="reviewed"):
        call_command("import_station_coordinates", "unused.json")
