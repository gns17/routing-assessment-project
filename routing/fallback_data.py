"""Versioned offline location hints, never station-coordinate imports or HTTP."""

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings


class FallbackDataError(ValueError):
    pass


def locality_key(city, state):
    city = unicodedata.normalize("NFKD", city).encode("ascii", "ignore").decode()
    return f"{state.upper()}:{re.sub(r'[^a-z0-9]+', ' ', city.casefold()).strip()}"


def content_version(document):
    body = {k: v for k, v in document.items() if k != "version"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class LocationCatalog:
    version: str
    localities: dict
    station_estimates: dict
    provenance: dict

    @classmethod
    def read(cls, path):
        try:
            document = json.loads(Path(path).read_text())
            if document["schema_version"] != 1 or document[
                "version"
            ] != content_version(document):
                raise ValueError
            if not isinstance(document["provenance"], dict):
                raise TypeError
            localities, estimates = {}, {}
            for row in document["localities"]:
                key = locality_key(row["city"], row["state"])
                if key in localities:
                    raise ValueError
                validate_point(row)
                validate_provenance(row)
                localities[key] = row
            for row in document.get("station_estimates", []):
                opis = row["opis_id"]
                if (
                    isinstance(opis, bool)
                    or not isinstance(opis, int)
                    or opis <= 0
                    or opis in estimates
                ):
                    raise ValueError
                if (
                    row["location_quality"] != "estimated_physical_station"
                    or row["identity_supported"] is not True
                    or row.get("contradictions")
                ):
                    raise ValueError
                if not re.fullmatch(r"[a-f0-9]{64}", row["location_fingerprint"]):
                    raise ValueError
                validate_point(row)
                validate_provenance(row)
                if not row["source"].get("license"):
                    raise ValueError
                if (
                    not isinstance(row.get("evidence"), str)
                    or not row["evidence"].strip()
                    or not isinstance(row.get("uncertainty"), dict)
                ):
                    raise ValueError
                # Null means unknown. A bound is road-chainage uncertainty, not a
                # geocoder confidence/radial distance converted into a road bound.
                bound = row.get("route_mile_uncertainty")
                if bound is not None and (
                    not finite(bound) or bound < 0 or not row.get("bound_evidence")
                ):
                    raise ValueError
                access = row.get("access_detour_bound_miles")
                if access is not None and (
                    not finite(access) or access < 0 or not row.get("bound_evidence")
                ):
                    raise ValueError
                estimates[opis] = row
            return cls(
                document["version"], localities, estimates, document["provenance"]
            )
        except (OSError, ValueError, KeyError, TypeError):
            raise FallbackDataError(
                "Offline best-effort location data is missing or invalid"
            ) from None


def finite(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def validate_point(row):
    if (
        not finite(row["latitude"])
        or not -90 <= row["latitude"] <= 90
        or not finite(row["longitude"])
        or not -180 <= row["longitude"] <= 180
    ):
        raise ValueError("Invalid location hint")


def validate_provenance(row):
    if (
        not isinstance(row["source"], dict)
        or not row["source"].get("url")
        or not row["source"].get("coordinate_method")
    ):
        raise ValueError("Location provenance is required")


@lru_cache(maxsize=1)
def get_location_catalog():
    # Deployment snapshot: restart workers after replacing prepared data. No
    # request-time reload/geocoding or hidden persistence framework.
    return LocationCatalog.read(settings.BEST_EFFORT_LOCATION_FILE)
