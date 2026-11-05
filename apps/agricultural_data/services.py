import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    AgriculturalDataset,
    DataImportJob,
    HistoricalCropObservation,
    HistoricalWeatherObservation,
    Region,
)


MAX_IMPORT_ROWS = 5000
MAX_IMPORT_BYTES = 5 * 1024 * 1024
WEATHER_REQUIRED_COLUMNS = {"district", "date"}
CROP_REQUIRED_COLUMNS = {"district", "crop_name", "year"}


class DataImportValidationError(ValidationError):
    pass


def _read_text(upload):
    raw = upload.read()
    if isinstance(raw, str):
        if len(raw.encode("utf-8")) > MAX_IMPORT_BYTES:
            raise DataImportValidationError("CSV files must be 5 MB or smaller.")
        return raw
    if len(raw) > MAX_IMPORT_BYTES:
        raise DataImportValidationError("CSV files must be 5 MB or smaller.")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DataImportValidationError("CSV files must use UTF-8 encoding.") from exc


def _decimal(value, field_name, row_number, minimum=None, maximum=None):
    value = (value or "").strip()
    if not value:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"row {row_number}: {field_name} must be numeric") from exc
    if minimum is not None and number < minimum:
        raise ValueError(f"row {row_number}: {field_name} must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"row {row_number}: {field_name} must not exceed {maximum}")
    return number


def _parse_date(value, row_number):
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError as exc:
        raise ValueError(f"row {row_number}: date must use YYYY-MM-DD") from exc


def _normalized_rows(text, required_columns):
    reader = csv.DictReader(io.StringIO(text))
    headings = {heading.strip().lower() for heading in (reader.fieldnames or []) if heading}
    missing = required_columns - headings
    if missing:
        raise DataImportValidationError(f"Missing required columns: {', '.join(sorted(missing))}")
    rows = []
    for row_number, row in enumerate(reader, start=2):
        if row_number - 1 > MAX_IMPORT_ROWS:
            raise DataImportValidationError(f"Imports are limited to {MAX_IMPORT_ROWS} data rows.")
        normalized = {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}
        if any(normalized.values()):
            rows.append((row_number, normalized))
    if not rows:
        raise DataImportValidationError("The CSV file does not contain any data rows.")
    return rows


def _region_for(row, row_number):
    district = row.get("district", "").strip()
    if not district:
        raise ValueError(f"row {row_number}: district is required")
    return Region.objects.get_or_create(
        district=district,
        upazila=row.get("upazila", "").strip(),
        defaults={
            "latitude": _decimal(row.get("latitude"), "latitude", row_number, Decimal("-90"), Decimal("90")),
            "longitude": _decimal(row.get("longitude"), "longitude", row_number, Decimal("-180"), Decimal("180")),
        },
    )[0]


def import_historical_csv(*, dataset, upload, kind, actor=None, filename=None):
    if kind not in {DataImportJob.Kind.WEATHER, DataImportJob.Kind.CROP}:
        raise DataImportValidationError("Unsupported import kind.")
    job = DataImportJob.objects.create(
        dataset=dataset,
        uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
        kind=kind,
        filename=(filename or getattr(upload, "name", "dataset.csv"))[:255],
        status=DataImportJob.Status.PROCESSING,
        started_at=timezone.now(),
    )
    try:
        text = _read_text(upload)
        required = WEATHER_REQUIRED_COLUMNS if kind == DataImportJob.Kind.WEATHER else CROP_REQUIRED_COLUMNS
        rows = _normalized_rows(text, required)
        job.rows_received = len(rows)
        parsed = []
        errors = []
        for row_number, row in rows:
            try:
                if kind == DataImportJob.Kind.WEATHER:
                    observed_on = _parse_date(row.get("date"), row_number)
                    quality_flag = row.get("quality_flag", "GOOD").upper() or "GOOD"
                    allowed_quality = {choice for choice, _ in HistoricalWeatherObservation.Quality.choices}
                    if quality_flag not in allowed_quality:
                        raise ValueError(
                            f"row {row_number}: quality_flag must be one of {', '.join(sorted(allowed_quality))}"
                        )
                    parsed.append(
                        {
                            "region_row": row,
                            "row_number": row_number,
                            "observed_on": observed_on,
                            "rainfall_mm": _decimal(row.get("rainfall_mm"), "rainfall_mm", row_number, Decimal("0")),
                            "temperature_min_c": _decimal(row.get("temperature_min_c"), "temperature_min_c", row_number),
                            "temperature_max_c": _decimal(row.get("temperature_max_c"), "temperature_max_c", row_number),
                            "temperature_mean_c": _decimal(row.get("temperature_mean_c"), "temperature_mean_c", row_number),
                            "humidity_percent": _decimal(row.get("humidity_percent"), "humidity_percent", row_number, Decimal("0"), Decimal("100")),
                            "quality_flag": quality_flag,
                            "notes": row.get("notes", "")[:300],
                        }
                    )
                else:
                    try:
                        year = int(row.get("year", ""))
                    except ValueError as exc:
                        raise ValueError(f"row {row_number}: year must be a whole number") from exc
                    if not 1900 <= year <= 2200:
                        raise ValueError(f"row {row_number}: year must be between 1900 and 2200")
                    crop_name = row.get("crop_name", "").strip()
                    if not crop_name:
                        raise ValueError(f"row {row_number}: crop_name is required")
                    parsed.append(
                        {
                            "region_row": row,
                            "row_number": row_number,
                            "crop_name": crop_name,
                            "variety": row.get("variety", "")[:100],
                            "year": year,
                            "season": row.get("season", "")[:80],
                            "cultivated_area_hectares": _decimal(row.get("cultivated_area_hectares"), "cultivated_area_hectares", row_number, Decimal("0")),
                            "production_tonnes": _decimal(row.get("production_tonnes"), "production_tonnes", row_number, Decimal("0")),
                            "yield_tonnes_per_hectare": _decimal(row.get("yield_tonnes_per_hectare"), "yield_tonnes_per_hectare", row_number, Decimal("0")),
                            "quality_notes": row.get("quality_notes", "")[:300],
                        }
                    )
            except ValueError as exc:
                errors.append(str(exc))
        if errors:
            raise DataImportValidationError(errors[:50])

        dates = []
        with transaction.atomic():
            for item in parsed:
                row_number = item.pop("row_number")
                region_row = item.pop("region_row")
                region = _region_for(region_row, row_number)
                if kind == DataImportJob.Kind.WEATHER:
                    observed_on = item.pop("observed_on")
                    dates.append(observed_on)
                    HistoricalWeatherObservation.objects.update_or_create(
                        dataset=dataset,
                        region=region,
                        observed_on=observed_on,
                        defaults=item,
                    )
                else:
                    year = item["year"]
                    dates.extend([date(year, 1, 1), date(year, 12, 31)])
                    lookup = {
                        "dataset": dataset,
                        "region": region,
                        "crop_name": item.pop("crop_name"),
                        "variety": item.pop("variety"),
                        "year": item.pop("year"),
                        "season": item.pop("season"),
                    }
                    HistoricalCropObservation.objects.update_or_create(**lookup, defaults=item)
            dataset.date_start = min(dates)
            dataset.date_end = max(dates)
            dataset.save(update_fields=["date_start", "date_end", "updated_at"])
        job.rows_imported = len(parsed)
        job.status = DataImportJob.Status.COMPLETED
        job.completed_at = timezone.now()
        job.save(update_fields=["rows_received", "rows_imported", "status", "completed_at"])
        return job
    except (DataImportValidationError, ValueError) as exc:
        messages = exc.messages if isinstance(exc, ValidationError) else [str(exc)]
        job.status = DataImportJob.Status.FAILED
        job.errors = messages[:50]
        job.completed_at = timezone.now()
        job.save(update_fields=["rows_received", "status", "errors", "completed_at"])
        raise DataImportValidationError(messages) from exc
