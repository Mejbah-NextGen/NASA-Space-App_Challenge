import csv
import hashlib
import io
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.agricultural_data.models import (
    AgriculturalDataset,
    CropDisease,
    DataImportJob,
    DataSource,
    DiseaseGuidance,
)
from apps.agricultural_data.services import MAX_IMPORT_BYTES, MAX_IMPORT_ROWS


REQUIRED_COLUMNS = {"crop", "disease", "information type", "information"}
SOURCE_NAME = "User-provided crop disease treatment dataset"
DATASET_TITLE = "Crop disease guidance reference"
DATASET_SLUG = "crop-disease-guidance-reference"
MAX_GUIDANCE_LENGTH = 5000


CATEGORY_PATTERNS = (
    (
        DiseaseGuidance.Category.IDENTIFICATION,
        re.compile(r"symptom|identif|diagnos|sign|appearance|feature|affected|damage|differen", re.I),
    ),
    (
        DiseaseGuidance.Category.BIOLOGICAL,
        re.compile(r"biological|organic|biocontrol|microbial|natural", re.I),
    ),
    (
        DiseaseGuidance.Category.TREATMENT,
        re.compile(
            r"chemical|fungicide|bactericide|spray|dosage|application|copper|bordeaux|"
            r"antibiotic|insecticide|treatment|curative|pesticide",
            re.I,
        ),
    ),
    (
        DiseaseGuidance.Category.PREVENTION,
        re.compile(
            r"prevent|cultural|sanitation|hygiene|prun|rotation|resistan|variet|soil|irrig|"
            r"water|nursery|weed|field|orchard|harvest|management|control|roug|removal|"
            r"spacing|mulch|quarantine|certif|planting|drain",
            re.I,
        ),
    ),
    (
        DiseaseGuidance.Category.BIOLOGY,
        re.compile(
            r"pathogen|caus|organism|cycle|biology|spread|transmi|survival|infection|"
            r"condition|weather|environment|epidemi|vector|overwinter|source of inoculum|mode of",
            re.I,
        ),
    ),
    (
        DiseaseGuidance.Category.IMPACT,
        re.compile(
            r"yield|loss|impact|economic|severity|importance|significance|monitor|threshold|"
            r"scout|decision|record|forecast",
            re.I,
        ),
    ),
)


def normalize_guidance_category(information_type):
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(information_type):
            return category
    return DiseaseGuidance.Category.OTHER


def _guidance_hash(information_type, content):
    payload = f"{information_type.casefold()}\0{content}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_rows(path):
    raw = path.read_bytes()
    if len(raw) > MAX_IMPORT_BYTES:
        raise CommandError(f"CSV files must be {MAX_IMPORT_BYTES // (1024 * 1024)} MB or smaller.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CommandError("The crop disease CSV must use UTF-8 encoding.") from exc

    reader = csv.DictReader(io.StringIO(text))
    headings = {heading.strip().lower() for heading in (reader.fieldnames or []) if heading}
    missing = REQUIRED_COLUMNS - headings
    if missing:
        raise CommandError(f"Missing required columns: {', '.join(sorted(missing))}")

    rows = []
    for source_row, row in enumerate(reader, start=2):
        if source_row - 1 > MAX_IMPORT_ROWS:
            raise CommandError(f"Imports are limited to {MAX_IMPORT_ROWS} data rows.")
        normalized = {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}
        if not any(normalized.values()):
            continue
        crop = normalized.get("crop", "")
        disease = normalized.get("disease", "")
        information_type = normalized.get("information type", "")
        content = normalized.get("information", "")
        missing_values = [
            label
            for label, value in (
                ("Crop", crop),
                ("Disease", disease),
                ("Information Type", information_type),
                ("Information", content),
            )
            if not value
        ]
        if missing_values:
            raise CommandError(f"Row {source_row} has blank required values: {', '.join(missing_values)}")
        if len(crop) > CropDisease._meta.get_field("crop_name").max_length:
            raise CommandError(f"Row {source_row}: Crop is too long.")
        if len(disease) > CropDisease._meta.get_field("disease_name").max_length:
            raise CommandError(f"Row {source_row}: Disease is too long.")
        if len(information_type) > DiseaseGuidance._meta.get_field("information_type").max_length:
            raise CommandError(f"Row {source_row}: Information Type is too long.")
        if len(content) > MAX_GUIDANCE_LENGTH:
            raise CommandError(f"Row {source_row}: Information must be {MAX_GUIDANCE_LENGTH} characters or fewer.")
        rows.append(
            {
                "source_row": source_row,
                "crop": crop,
                "disease": disease,
                "information_type": information_type,
                "category": normalize_guidance_category(information_type),
                "content": content,
                "content_hash": _guidance_hash(information_type, content),
            }
        )
    if not rows:
        raise CommandError("The crop disease CSV does not contain any data rows.")
    return raw, rows


def import_crop_disease_file(path):
    """Import a validated crop-disease CSV and return a reproducible summary."""

    raw, rows = _read_rows(path)
    unique_rows = {}
    for row in rows:
        key = (
            row["crop"].casefold(),
            row["disease"].casefold(),
            row["information_type"].casefold(),
            row["content"],
        )
        unique_rows.setdefault(key, row)

    canonical_pairs = {}
    for row in unique_rows.values():
        pair_key = (row["crop"].casefold(), row["disease"].casefold())
        canonical_pairs.setdefault(pair_key, (row["crop"], row["disease"]))
        row["canonical_pair"] = canonical_pairs[pair_key]

    now = timezone.now()
    file_hash = hashlib.sha256(raw).hexdigest().upper()
    with transaction.atomic():
        source, _ = DataSource.objects.update_or_create(
            name=SOURCE_NAME,
            defaults={
                "provider": "Project contributor",
                "kind": DataSource.Kind.DISEASE,
                "url": "",
                "description": "A contributor-supplied narrative crop disease reference dataset.",
                "attribution": "User-provided project dataset; not a NASA dataset.",
                "geographic_coverage": "Not specified by the contributor",
                "update_frequency": "Static project import",
                "limitations": (
                    "No original citations, license, author, review date, regulatory jurisdiction, or "
                    "geographic scope were supplied. Treatment guidance requires local professional review."
                ),
                "is_active": True,
                "is_demo": True,
                "last_updated_at": now,
            },
        )
        dataset, _ = AgriculturalDataset.objects.update_or_create(
            slug=DATASET_SLUG,
            defaults={
                "source": source,
                "title": DATASET_TITLE,
                "description": (
                    "Searchable crop disease symptoms, prevention, biology, monitoring, and treatment "
                    "reference entries supplied for this project."
                ),
                "status": AgriculturalDataset.Status.SAMPLE,
                "geographic_coverage": "Unspecified; general crop reference",
                "date_start": None,
                "date_end": None,
                "units": "Narrative guidance entries",
                "quality_notes": (
                    "Unverified contributor data. Chemical names, rates, intervals, and permitted uses "
                    "must be checked with a qualified local agriculturalist and the current product label."
                ),
            },
        )

        pairs = set(canonical_pairs.values())
        existing_diseases = list(
            CropDisease.objects.filter(dataset=dataset).prefetch_related("guidance_entries")
        )
        logical_pairs_before = {
            (item.crop_name.casefold(), item.disease_name.casefold()) for item in existing_diseases
        }
        guidance_count_before = sum(len(item.guidance_entries.all()) for item in existing_diseases)
        CropDisease.objects.bulk_create(
            [
                CropDisease(dataset=dataset, crop_name=crop, disease_name=disease)
                for crop, disease in sorted(pairs)
            ],
            ignore_conflicts=True,
            batch_size=500,
        )
        disease_map = {
            (item.crop_name, item.disease_name): item
            for item in CropDisease.objects.filter(dataset=dataset)
        }

        # Older imports may have produced two pairs that differ only in capitalization.
        # Merge those records into the first spelling used by the current file.
        for item in existing_diseases:
            pair_key = (item.crop_name.casefold(), item.disease_name.casefold())
            canonical_pair = canonical_pairs.get(pair_key)
            if not canonical_pair:
                continue
            canonical_disease = disease_map[canonical_pair]
            if item.pk == canonical_disease.pk:
                continue
            for entry in item.guidance_entries.all():
                DiseaseGuidance.objects.get_or_create(
                    disease=canonical_disease,
                    content_hash=entry.content_hash,
                    defaults={
                        "information_type": entry.information_type,
                        "category": entry.category,
                        "content": entry.content,
                        "source_row": entry.source_row,
                    },
                )
            item.delete()

        DiseaseGuidance.objects.bulk_create(
            [
                DiseaseGuidance(
                    disease=disease_map[row["canonical_pair"]],
                    information_type=row["information_type"],
                    category=row["category"],
                    content=row["content"],
                    content_hash=row["content_hash"],
                    source_row=row["source_row"],
                )
                for row in unique_rows.values()
            ],
            ignore_conflicts=True,
            batch_size=500,
        )

        pair_count = CropDisease.objects.filter(dataset=dataset).count()
        guidance_count = DiseaseGuidance.objects.filter(disease__dataset=dataset).count()
        crop_count = (
            CropDisease.objects.filter(dataset=dataset)
            .order_by()
            .values("crop_name")
            .distinct()
            .count()
        )
        dataset.metadata = {
            "source_filename": path.name,
            "sha256": file_hash,
            "rows_received": len(rows),
            "unique_guidance_rows": len(unique_rows),
            "duplicate_rows_skipped": len(rows) - len(unique_rows),
            "crop_count": crop_count,
            "crop_disease_pairs": pair_count,
            "normalization_version": 1,
        }
        dataset.save(update_fields=["metadata", "updated_at"])
        DataImportJob.objects.create(
            dataset=dataset,
            kind=DataImportJob.Kind.DISEASE,
            filename=path.name[:255],
            status=DataImportJob.Status.COMPLETED,
            rows_received=len(rows),
            rows_imported=len(unique_rows),
            started_at=now,
            completed_at=timezone.now(),
        )

    return {
        "dataset": dataset,
        "rows_received": len(rows),
        "unique_rows": len(unique_rows),
        "duplicates": len(rows) - len(unique_rows),
        "crop_count": crop_count,
        "pair_count": pair_count,
        "pairs_created": max(0, pair_count - len(logical_pairs_before)),
        "guidance_count": guidance_count,
        "guidance_created": guidance_count - guidance_count_before,
        "sha256": file_hash,
    }


class Command(BaseCommand):
    help = "Import a contributor-supplied crop disease guidance CSV as explicitly unverified sample data."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")

    def handle(self, *args, **options):
        path = Path(options["csv_path"]).resolve()
        if not path.is_file() or path.suffix.lower() != ".csv":
            raise CommandError("csv_path must point to an existing .csv file")

        summary = import_crop_disease_file(path)
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {summary['rows_received']} rows ({summary['unique_rows']} unique); "
                f"created {summary['guidance_created']} guidance entries and "
                f"{summary['pairs_created']} crop/disease pairs."
            )
        )
        self.stdout.write(
            f"Library totals: {summary['crop_count']} crops, {summary['pair_count']} crop/disease pairs, "
            f"{summary['guidance_count']} guidance entries; {summary['duplicates']} duplicate input rows skipped."
        )
        self.stdout.write(
            self.style.WARNING(
                "Dataset status is SAMPLE/unverified. It is not NASA data; treatment instructions require "
                "qualified local review and current product-label verification."
            )
        )
