"""ORM boundary returning plain candidates and their consistent revision."""

from django.db import transaction
from django.db.models import F

from routing.geometry import Candidate
from routing.models import DatasetState, Station


class StationRepository:
    def snapshot(self, bounds):
        south, north, west, east = bounds
        with transaction.atomic():
            revision = (
                DatasetState.objects.values_list("revision", flat=True).first() or 0
            )
            rows = (
                Station.objects.filter(
                    active=True,
                    enrichment_status="accepted",
                    enrichment_fingerprint=F("location_fingerprint"),
                    latitude__range=(south, north),
                    longitude__range=(west, east),
                    price__gt=0,
                )
                .exclude(enrichment_policy="")
                .values_list(
                    "opis_id",
                    "name",
                    "address",
                    "city",
                    "state",
                    "price",
                    "latitude",
                    "longitude",
                )
            )
            return revision, [Candidate(*row) for row in rows]


class BestEffortRepository:
    """Read seed identities/prices and approved coordinates in one consistent snapshot."""

    def snapshot(self):
        from routing.best_effort import SeedStation

        with transaction.atomic():
            revision = (
                DatasetState.objects.values_list("revision", flat=True).first() or 0
            )
            rows = Station.objects.filter(active=True, price__gt=0).values_list(
                "opis_id",
                "name",
                "address",
                "city",
                "state",
                "price",
                "location_fingerprint",
                "latitude",
                "longitude",
                "enrichment_status",
                "enrichment_fingerprint",
                "enrichment_policy",
                "enrichment_metadata",
            )
            return revision, [SeedStation(*row) for row in rows]
