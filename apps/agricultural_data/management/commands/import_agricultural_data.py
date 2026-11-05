from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.agricultural_data.models import AgriculturalDataset, DataImportJob, DataSource
from apps.agricultural_data.services import DataImportValidationError, import_historical_csv


class Command(BaseCommand):
    help = "Import validated historical weather or crop observations from a UTF-8 CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--kind", choices=["weather", "crop"], required=True)
        parser.add_argument("--source", required=True)
        parser.add_argument("--title", required=True)
        parser.add_argument("--verified", action="store_true")

    def handle(self, *args, **options):
        path = Path(options["csv_path"]).resolve()
        if not path.is_file() or path.suffix.lower() != ".csv":
            raise CommandError("csv_path must point to an existing .csv file")
        kind = DataImportJob.Kind.WEATHER if options["kind"] == "weather" else DataImportJob.Kind.CROP
        source_kind = DataSource.Kind.HISTORICAL_WEATHER if kind == DataImportJob.Kind.WEATHER else DataSource.Kind.CROP
        source, _ = DataSource.objects.get_or_create(
            name=options["source"],
            defaults={"provider": options["source"], "kind": source_kind, "is_demo": not options["verified"]},
        )
        slug = slugify(options["title"])
        dataset, _ = AgriculturalDataset.objects.get_or_create(
            slug=slug,
            defaults={
                "source": source,
                "title": options["title"],
                "status": AgriculturalDataset.Status.VERIFIED if options["verified"] else AgriculturalDataset.Status.SAMPLE,
            },
        )
        try:
            with path.open("rb") as upload:
                job = import_historical_csv(dataset=dataset, upload=upload, kind=kind, filename=path.name)
        except DataImportValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        self.stdout.write(self.style.SUCCESS(f"Imported {job.rows_imported} rows into {dataset.title}."))
