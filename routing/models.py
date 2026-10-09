from django.db import models
from django.db.models import F, Q


class DatasetState(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    revision = models.PositiveBigIntegerField(default=0)
    source_checksum = models.CharField(max_length=64, blank=True)
    import_policy = models.CharField(max_length=40, default="csv-min-price-v1")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name="dataset_singleton")
        ]


class Station(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        ACCEPTED = "accepted"
        AMBIGUOUS = "ambiguous"
        REJECTED = "rejected"

    opis_id = models.PositiveBigIntegerField(unique=True)
    name = models.CharField(max_length=300)
    aliases = models.JSONField(default=list)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=8)
    price_min = models.DecimalField(max_digits=12, decimal_places=8)
    price_max = models.DecimalField(max_digits=12, decimal_places=8)
    source_prices = models.JSONField(default=list)
    source_rows = models.JSONField(default=list)
    source_checksum = models.CharField(max_length=64)
    active = models.BooleanField(default=True)
    location_fingerprint = models.CharField(max_length=64)
    latitude = models.FloatField(null=True, blank=True, db_index=True)
    longitude = models.FloatField(null=True, blank=True, db_index=True)
    enrichment_status = models.CharField(
        max_length=10, choices=Status, default=Status.PENDING
    )
    enrichment_fingerprint = models.CharField(max_length=64, blank=True)
    enrichment_policy = models.CharField(max_length=40, blank=True)
    enrichment_metadata = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gt=0, price_min__gt=0, price_max__gte=F("price_min"))
                & Q(price__gte=F("price_min"), price__lte=F("price_max")),
                name="station_valid_prices",
            ),
            models.CheckConstraint(
                condition=(
                    Q(latitude__isnull=True, longitude__isnull=True)
                    | Q(
                        latitude__isnull=False,
                        longitude__isnull=False,
                        latitude__gte=-90,
                        latitude__lte=90,
                        longitude__gte=-180,
                        longitude__lte=180,
                    )
                ),
                name="station_valid_coordinates",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(enrichment_status="accepted")
                    | (
                        Q(latitude__isnull=False, longitude__isnull=False)
                        & Q(enrichment_fingerprint=F("location_fingerprint"))
                        & ~Q(enrichment_policy="")
                    )
                ),
                name="accepted_station_has_current_coordinates",
            ),
            models.CheckConstraint(
                condition=Q(opis_id__gt=0, rack_id__gt=0), name="station_positive_ids"
            ),
            models.CheckConstraint(
                condition=Q(
                    enrichment_status__in=[
                        "pending",
                        "accepted",
                        "ambiguous",
                        "rejected",
                    ]
                ),
                name="station_known_status",
            ),
        ]
