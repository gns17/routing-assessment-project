"""Prepare locality hints from an already downloaded Census text/ZIP; no DB writes."""

import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from routing.fallback_data import LocationCatalog, content_version, locality_key
from routing.importing import parse_csv
from routing.provider import US_STATES

SOURCE_URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_place_national.zip"
SUFFIX = re.compile(
    r"\s+(?:city|town|village|borough|municipality|CDP|(?:unified|metropolitan) government)(?:\s+\(balance\))?$",
    re.IGNORECASE,
)


class Command(BaseCommand):
    help = "Prepare versioned offline hints, without querying or writing SQLite"

    def add_arguments(self, parser):
        parser.add_argument("gazetteer", type=Path)
        parser.add_argument("--csv", type=Path, default=Path("data/fuel-prices.csv"))
        parser.add_argument(
            "--output", type=Path, default=Path("data/best-effort-locations.json")
        )
        parser.add_argument("--station-estimates", type=Path)

    def handle(self, *args, **options):
        import hashlib

        try:
            raw = options["gazetteer"].read_bytes()
            if len(raw) > 10 * 1024**2:
                raise ValueError("Input exceeds bounded preparation size")
            if zipfile.is_zipfile(io.BytesIO(raw)):
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    members = [
                        m for m in archive.infolist() if m.filename.endswith(".txt")
                    ]
                    if len(members) != 1 or members[0].file_size > 12 * 1024**2:
                        raise ValueError("Unexpected or oversized ZIP")
                    text = archive.read(members[0]).decode("utf-8-sig")
            else:
                text = raw.decode("utf-8-sig")
            # Census editions can be pipe- or tab-delimited; require the same fields.
            delimiter = "|" if "|" in text.splitlines()[0] else "\t"
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            if not {"USPS", "GEOID", "NAME", "INTPTLAT", "INTPTLONG"} <= {
                s.strip() for s in reader.fieldnames or []
            }:
                raise ValueError("Unexpected Census fields")
            source, checksum, _ = parse_csv(options["csv"])
            wanted = {
                locality_key(r["city"], r["state"]): (r["city"], r["state"])
                for r in source.values()
            }
            groups = defaultdict(list)
            parsed = 0
            for item in reader:
                item = {k.strip(): (v or "").strip() for k, v in item.items()}
                parsed += 1
                if item["USPS"] not in US_STATES:
                    continue
                name = SUFFIX.sub("", item["NAME"])
                key = locality_key(name, item["USPS"])
                if key not in wanted:
                    continue
                city, state = wanted[key]
                groups[key].append(
                    {
                        "city": city,
                        "state": state,
                        "latitude": float(item["INTPTLAT"]),
                        "longitude": float(item["INTPTLONG"]),
                        "source": {
                            "url": SOURCE_URL,
                            "geoid": item["GEOID"],
                            "name": item["NAME"],
                            "coordinate_method": "Census representative internal point; NOT station site or entrance",
                        },
                    }
                )
            # Duplicate locality names can describe different municipalities. Do
            # not pick the closest one or guess postal/neighboring-city aliases.
            locations = [
                rows[0] for key, rows in sorted(groups.items()) if len(rows) == 1
            ]
            estimates = (
                json.loads(options["station_estimates"].read_text())
                if options["station_estimates"]
                else []
            )
            for estimate in estimates:
                seed = source.get(estimate["opis_id"])
                if (
                    seed is None
                    or seed["location_fingerprint"] != estimate["location_fingerprint"]
                ):
                    raise ValueError("Unknown/stale estimated identity")
            document = {
                "schema_version": 1,
                "localities": locations,
                "station_estimates": estimates,
                "provenance": {
                    "provider": "US Census Bureau",
                    "edition": 2025,
                    "license": "US government-produced data, public domain in the United States; retain attribution",
                    "license_url": "https://www2.census.gov/foia/ds_policies/ds027.pdf",
                    "license_scope": "Census locality records only; optional estimated sites retain their own source terms",
                    "source_url": SOURCE_URL,
                    "source_sha256": hashlib.sha256(raw).hexdigest(),
                    "seed_sha256": checksum,
                    "normalization": "ascii lowercase punctuation/whitespace; documented Census suffix removal only",
                },
            }
            document["version"] = content_version(document)
            output = options["output"]
            temporary = output.with_name(output.name + ".tmp")
            temporary.write_text(json.dumps(document, indent=2) + "\n")
            try:
                LocationCatalog.read(
                    temporary
                )  # Complete validation before atomic file replacement.
                temporary.replace(output)
            finally:
                temporary.unlink(missing_ok=True)
            keys = {locality_key(p["city"], p["state"]) for p in locations}
            self.stdout.write(
                json.dumps(
                    {
                        "source_places": parsed,
                        "unique_csv_localities": len(wanted),
                        "usable_localities": len(keys),
                        "stations_with_locality": sum(
                            locality_key(r["city"], r["state"]) in keys
                            for r in source.values()
                        ),
                        "excluded_ambiguous_keys": sum(
                            len(rows) > 1 for rows in groups.values()
                        ),
                        "estimated_physical_stations": len(estimates),
                        "version": document["version"],
                    }
                )
            )
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            UnicodeError,
            zipfile.BadZipFile,
        ) as error:
            raise CommandError(f"Unable to prepare best-effort data: {error}") from None
