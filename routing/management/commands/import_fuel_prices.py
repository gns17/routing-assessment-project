import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from routing.importing import import_csv


class Command(BaseCommand):
    help = "Validate/deduplicate immutable source CSV and persist US stations; no geocoding"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            type=Path,
            default=settings.BASE_DIR / "data/fuel-prices.csv",
        )
        parser.add_argument(
            "--full-snapshot",
            action="store_true",
            help="Mark stations absent from this validated full snapshot inactive",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            json.dumps(import_csv(options["path"], options["full_snapshot"]))
        )
