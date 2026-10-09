import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F

from routing.models import DatasetState, Station
from routing.provider import number


class Command(BaseCommand):
    help = "Import manually reviewed coordinate evidence; makes no external requests"

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report changes without writing",
        )
        parser.add_argument(
            "--reviewed",
            action="store_true",
            help="Confirm the artifact's identities/coordinates were reviewed",
        )

    def handle(self, *args, **options):
        if not options["reviewed"]:
            raise CommandError(
                "Coordinate import requires an explicitly reviewed artifact"
            )
        try:
            records = json.loads(options["path"].read_text())
            if not isinstance(records, list) or not records:
                raise ValueError
            ids = set()
            for item in records:
                if (
                    not isinstance(item, dict)
                    or item.get("synthetic")
                    or item.get("identity_verified") is not True
                ):
                    raise ValueError
                opis = item["opis_id"]
                if (
                    not isinstance(opis, int)
                    or isinstance(opis, bool)
                    or opis <= 0
                    or opis in ids
                ):
                    raise ValueError
                ids.add(opis)
                if not number(item["latitude"], -90, 90) or not number(
                    item["longitude"], -180, 180
                ):
                    raise ValueError
                for key, length in [
                    ("location_fingerprint", 64),
                    ("policy", 40),
                    ("source", 500),
                    ("evidence", 4000),
                ]:
                    if (
                        not isinstance(item[key], str)
                        or not 0 < len(item[key]) <= length
                    ):
                        raise ValueError
                if len(item["location_fingerprint"]) != 64:
                    raise ValueError
        except (OSError, ValueError, KeyError, TypeError):
            raise CommandError("Invalid reviewed coordinate artifact") from None
        with transaction.atomic():
            stations = Station.objects.in_bulk(ids, field_name="opis_id")
            if set(stations) != ids or any(
                not stations[i["opis_id"]].active
                or stations[i["opis_id"]].location_fingerprint
                != i["location_fingerprint"]
                for i in records
            ):
                raise CommandError(
                    "Unknown, inactive or stale station identity in artifact"
                )
            changes = []
            for item in records:
                station = stations[item["opis_id"]]
                values = {
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "enrichment_status": Station.Status.ACCEPTED,
                    "enrichment_fingerprint": item["location_fingerprint"],
                    "enrichment_policy": item["policy"],
                    "enrichment_metadata": {
                        "identity_verified": True,
                        "source": item["source"],
                        "evidence": item["evidence"],
                    },
                }
                if any(getattr(station, k) != v for k, v in values.items()):
                    for key, value in values.items():
                        setattr(station, key, value)
                    changes.append(station)
            if options["dry_run"]:
                revision = (
                    DatasetState.objects.filter(pk=1)
                    .values_list("revision", flat=True)
                    .first()
                    or 0
                )
                self.stdout.write(
                    json.dumps(
                        {
                            "dry_run": True,
                            "opis_ids": sorted(ids),
                            "would_update_ids": sorted(s.opis_id for s in changes),
                            "would_accept": len(changes),
                            "current_revision": revision,
                            "would_increment_revision": bool(changes),
                        }
                    )
                )
                return
            Station.objects.bulk_update(
                changes,
                [
                    "latitude",
                    "longitude",
                    "enrichment_status",
                    "enrichment_fingerprint",
                    "enrichment_policy",
                    "enrichment_metadata",
                ],
                batch_size=200,
            )
            state, _ = DatasetState.objects.get_or_create(pk=1)
            if changes:
                DatasetState.objects.filter(pk=state.pk).update(
                    revision=F("revision") + 1
                )
        self.stdout.write(json.dumps({"accepted": len(changes)}))
