"""Validated seed ingestion. Does not infer or request station coordinates."""

import csv
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import F

from routing.models import DatasetState, Station
from routing.provider import US_STATES

HEADERS = [
    "OPIS Truckstop ID",
    "Truckstop Name",
    "Address",
    "City",
    "State",
    "Rack ID",
    "Retail Price",
]
CANADIAN_STATES = {
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NS",
    "NT",
    "NU",
    "ON",
    "PE",
    "QC",
    "SK",
    "YT",
}
IMPORT_FIELDS = [
    "name",
    "aliases",
    "address",
    "city",
    "state",
    "rack_id",
    "price",
    "price_min",
    "price_max",
    "source_prices",
    "source_rows",
    "source_checksum",
    "active",
    "location_fingerprint",
]
LOCATION_FIELDS = [
    "latitude",
    "longitude",
    "enrichment_status",
    "enrichment_fingerprint",
    "enrichment_policy",
    "enrichment_metadata",
]


def location_fingerprint(record):
    # Stable location-only identity; prices/checksums/row numbers are excluded.
    values = [
        str(record[k]).casefold()
        for k in ["opis_id", "name", "address", "city", "state"]
    ]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def parse_csv(path):
    try:
        raw = Path(path).read_bytes()
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeError):
        raise CommandError("Unable to read UTF-8 source CSV") from None
    checksum = hashlib.sha256(raw).hexdigest()
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    if reader.fieldnames != HEADERS:
        raise CommandError("Unexpected CSV headers")
    records, excluded, row_count = {}, 0, 0
    try:
        for line, row in enumerate(reader, 2):
            row_count += 1
            if None in row or any(not (row.get(k) or "").strip() for k in HEADERS):
                raise ValueError("missing or extra fields")
            row = {k: " ".join(v.split()) for k, v in row.items()}
            row["State"] = row["State"].upper()
            if any(
                len(row[k]) > limit
                for k, limit in [
                    ("Truckstop Name", 300),
                    ("Address", 300),
                    ("City", 100),
                ]
            ):
                raise ValueError("location field exceeds supported length")
            if row["State"] not in US_STATES | {"AK", "HI"} | CANADIAN_STATES:
                raise ValueError("unknown state/province")
            for key in ("OPIS Truckstop ID", "Rack ID"):
                if not row[key].isdigit() or int(row[key]) <= 0:
                    raise ValueError("invalid numeric ID")
                limit = 2**63 - 1 if key == "OPIS Truckstop ID" else 2**31 - 1
                if int(row[key]) > limit:
                    raise ValueError("numeric ID out of range")
            price = Decimal(row["Retail Price"])
            if (
                not price.is_finite()
                or not 0 < price < Decimal(10000)
                or price != price.quantize(Decimal("0.00000001"))
            ):
                raise ValueError("invalid price or excess precision")
            if row["State"] in CANADIAN_STATES:
                excluded += 1
                continue
            opis_id = int(row["OPIS Truckstop ID"])
            record = records.setdefault(
                opis_id,
                {
                    "opis_id": opis_id,
                    "name": row["Truckstop Name"],
                    "aliases": [],
                    "address": row["Address"],
                    "city": row["City"],
                    "state": row["State"],
                    "rack_id": int(row["Rack ID"]),
                    "source_rows": [],
                    "source_prices": [],
                    "source_checksum": checksum,
                    "active": True,
                },
            )
            if any(
                str(record[k]).casefold() != str(v).casefold()
                for k, v in (
                    ("address", row["Address"]),
                    ("city", row["City"]),
                    ("state", row["State"]),
                    ("rack_id", int(row["Rack ID"])),
                )
            ):
                raise ValueError("conflicting station location/rack")
            record["aliases"].append(row["Truckstop Name"])
            record["source_rows"].append(line)
            record["source_prices"].append(price)
    except (ValueError, InvalidOperation, csv.Error) as error:
        raise CommandError(
            f"CSV validation failed near row {reader.line_num}: {error}"
        ) from None
    if not records:
        raise CommandError("CSV contains no eligible US stations")
    for record in records.values():
        record["aliases"] = sorted(
            set(record["aliases"]), key=lambda s: (s.casefold(), s)
        )
        record["name"] = record["aliases"][0]
        prices = sorted(set(record["source_prices"]))
        record.update(price=prices[0], price_min=prices[0], price_max=prices[-1])
        record["source_prices"] = [str(p) for p in prices]
        record["location_fingerprint"] = location_fingerprint(record)
    return (
        records,
        checksum,
        {
            "source_rows": row_count,
            "excluded_non_us_rows": excluded,
            "unique_us_stations": len(records),
        },
    )


def import_csv(path, full_snapshot=False):
    records, checksum, summary = parse_csv(path)  # Complete validation precedes writes.
    with transaction.atomic():
        state, _ = DatasetState.objects.get_or_create(pk=1)
        existing = {s.opis_id: s for s in Station.objects.all()}
        creates, updates = [], []
        for opis_id, record in records.items():
            station = existing.get(opis_id)
            if station is None:
                creates.append(Station(**record))
                continue
            changed_location = (
                station.location_fingerprint != record["location_fingerprint"]
            )
            changed = any(getattr(station, key) != record[key] for key in IMPORT_FIELDS)
            if not changed:
                continue
            for key in IMPORT_FIELDS:
                setattr(station, key, record[key])
            if changed_location:
                station.latitude = station.longitude = None
                station.enrichment_status = Station.Status.PENDING
                station.enrichment_fingerprint = station.enrichment_policy = ""
                station.enrichment_metadata = {}
            updates.append(station)
        Station.objects.bulk_create(creates, batch_size=200)
        Station.objects.bulk_update(
            updates, IMPORT_FIELDS + LOCATION_FIELDS, batch_size=200
        )
        removed = 0
        if full_snapshot:
            removed = (
                Station.objects.filter(active=True)
                .exclude(opis_id__in=records)
                .update(active=False)
            )
        if creates or updates or removed or state.source_checksum != checksum:
            DatasetState.objects.filter(pk=1).update(
                revision=F("revision") + 1,
                source_checksum=checksum,
                import_policy="csv-min-price-v1",
            )
        state.refresh_from_db()
    return {
        **summary,
        "created": len(creates),
        "updated": len(updates),
        "deactivated": removed,
        "revision": state.revision,
    }
