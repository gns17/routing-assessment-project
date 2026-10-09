import io
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


def test_dry_run_validates_without_station_or_revision_writes(tmp_path, monkeypatch):
    import_csv(source(tmp_path, [row()]))
    item = Station.objects.get()
    before = list(Station.objects.values())
    state = list(DatasetState.objects.values())
    path = artifact(tmp_path, record(item))

    def fail(*args, **kwargs):
        raise AssertionError("Dry run must never write")

    monkeypatch.setattr(Station.objects, "bulk_update", fail)
    output = io.StringIO()
    call_command(
        "import_station_coordinates",
        str(path),
        reviewed=True,
        dry_run=True,
        stdout=output,
    )
    result = json.loads(output.getvalue())
    assert result["would_accept"] == 1 and result["would_update_ids"] == [item.opis_id]
    assert result["would_increment_revision"]
    assert list(Station.objects.values()) == before
    assert list(DatasetState.objects.values()) == state


def test_dry_run_reports_no_changes_after_identical_import(tmp_path):
    import_csv(source(tmp_path, [row()]))
    path = artifact(tmp_path, record(Station.objects.get()))
    call_command("import_station_coordinates", str(path), reviewed=True)
    output = io.StringIO()
    call_command(
        "import_station_coordinates",
        str(path),
        reviewed=True,
        dry_run=True,
        stdout=output,
    )
    result = json.loads(output.getvalue())
    assert result["would_accept"] == 0 and not result["would_increment_revision"]


def test_dry_run_rejects_stale_identity(tmp_path):
    import_csv(source(tmp_path, [row()]))
    entry = {**record(Station.objects.get()), "location_fingerprint": "f" * 64}
    with pytest.raises(CommandError, match="stale"):
        call_command(
            "import_station_coordinates",
            str(artifact(tmp_path, entry)),
            reviewed=True,
            dry_run=True,
        )
    assert Station.objects.get().latitude is None
