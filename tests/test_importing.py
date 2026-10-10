import csv
import io
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction

from routing.importing import HEADERS, import_csv
from routing.models import DatasetState, Station

pytestmark = pytest.mark.django_db


def source(tmp_path, rows):
    path = tmp_path / "source.csv"
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS)
        writer.writerows(rows)
    return path


def row(
    opis=7,
    name="Example Fuel",
    address="US-180",
    city="Carlsbad",
    state="NM",
    rack=10,
    price="3.00733333",
):
    return [opis, name, address, city, state, rack, price]


def accept(station):
    station.latitude, station.longitude = 32.4, -104.2
    station.enrichment_status = Station.Status.ACCEPTED
    station.enrichment_fingerprint = station.location_fingerprint
    station.enrichment_policy = "synthetic-test-only"
    station.save()


def test_normalization_duplicates_canada_and_idempotence(tmp_path):
    path = source(
        tmp_path,
        [
            row(city=" Carlsbad  "),
            row(name="Example Fuel Center", price="3.2"),
            row(),
            row(opis=9, state="ON"),
        ],
    )
    result = import_csv(path)
    assert result["created"] == 1 and result["excluded_non_us_rows"] == 1
    item = Station.objects.get()
    assert item.city == "Carlsbad"
    assert item.price == item.price_min == Decimal("3.00733333")
    assert item.price_max == Decimal("3.2")
    assert len(item.source_rows) == 3 and len(item.aliases) == 2
    assert item.latitude is None and item.enrichment_status == "pending"
    assert import_csv(path)["revision"] == result["revision"]
    assert Station.objects.count() == 1


def test_price_only_import_retains_coords_location_change_invalidates(tmp_path):
    path = source(tmp_path, [row()])
    import_csv(path)
    item = Station.objects.get()
    accept(item)
    original = item.location_fingerprint
    source(tmp_path, [row(price="2.9")])
    import_csv(path)
    item.refresh_from_db()
    assert item.enrichment_status == "accepted" and item.latitude == 32.4
    assert item.location_fingerprint == original
    source(tmp_path, [row(address="Another highway", price="2.9")])
    import_csv(path)
    item.refresh_from_db()
    assert item.latitude is None and item.longitude is None
    assert item.enrichment_status == "pending"
    assert item.location_fingerprint != original


@pytest.mark.parametrize(
    "bad",
    [
        row(price="NaN"),
        row(price="0"),
        row(price="3.123456789"),
        row(state="ZZ"),
        row(opis="abc"),
        row(city=""),
        row(rack=-1),
    ],
)
def test_invalid_full_file_causes_no_writes(tmp_path, bad):
    with pytest.raises(CommandError):
        import_csv(source(tmp_path, [row(), bad]))
    assert Station.objects.count() == DatasetState.objects.count() == 0


def test_conflicting_location_fails_before_writes(tmp_path):
    with pytest.raises(CommandError, match="conflicting"):
        import_csv(source(tmp_path, [row(), row(city="Different city")]))
    assert Station.objects.count() == 0


def test_database_failure_rolls_back_station_and_revision(tmp_path, monkeypatch):
    path = source(tmp_path, [row()])
    import_csv(path)
    revision = DatasetState.objects.get().revision
    source(tmp_path, [row(price=2), row(opis=8)])

    def fail(*args, **kwargs):
        raise RuntimeError("simulated write failure")

    monkeypatch.setattr(Station.objects, "bulk_update", fail)
    with pytest.raises(RuntimeError):
        import_csv(path)
    assert Station.objects.count() == 1
    assert Station.objects.get().price == Decimal("3.00733333")
    assert DatasetState.objects.get().revision == revision


def test_full_snapshot_deactivation_is_explicit(tmp_path):
    path = source(tmp_path, [row(), row(opis=8)])
    import_csv(path)
    source(tmp_path, [row()])
    import_csv(path)
    assert Station.objects.get(opis_id=8).active
    assert import_csv(path, full_snapshot=True)["deactivated"] == 1
    assert not Station.objects.get(opis_id=8).active


def test_database_rejects_stale_accepted_coordinates(tmp_path):
    import_csv(source(tmp_path, [row()]))
    item = Station.objects.get()
    with pytest.raises(IntegrityError), transaction.atomic():
        Station.objects.filter(pk=item.pk).update(
            latitude=32,
            longitude=-104,
            enrichment_status="accepted",
            enrichment_fingerprint="wrong",
            enrichment_policy="test",
        )


def test_command_summary(tmp_path):
    output = io.StringIO()
    call_command("import_fuel_prices", str(source(tmp_path, [row()])), stdout=output)
    assert '"created": 1' in output.getvalue()


def test_supplied_snapshot(tmp_path):
    from pathlib import Path

    result = import_csv(Path(__file__).resolve().parents[1] / "data/fuel-prices.csv")
    assert result["unique_us_stations"] == Station.objects.count() == 6626
    assert result["excluded_non_us_rows"] == 620
    assert (
        Station.objects.filter(
            enrichment_status="pending", latitude__isnull=True
        ).count()
        == 6626
    )
