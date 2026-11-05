from io import BytesIO

from django.test import TestCase
from django.urls import reverse

from .models import AgriculturalDataset, DataImportJob, DataSource, HistoricalCropObservation, HistoricalWeatherObservation, Region
from .services import DataImportValidationError, import_historical_csv


class HistoricalCsvImportTests(TestCase):
    def setUp(self):
        self.source = DataSource.objects.create(
            name="Test source",
            provider="Test provider",
            kind=DataSource.Kind.HISTORICAL_WEATHER,
            is_demo=True,
        )
        self.dataset = AgriculturalDataset.objects.create(
            source=self.source,
            title="Test dataset",
            slug="test-dataset",
            status=AgriculturalDataset.Status.SAMPLE,
        )

    def test_imports_valid_weather_csv_idempotently(self):
        body = b"district,upazila,date,rainfall_mm,temperature_mean_c,humidity_percent\nKurigram,Sadar,2025-01-01,12.5,24.1,71\n"
        first = import_historical_csv(
            dataset=self.dataset,
            upload=BytesIO(body),
            kind=DataImportJob.Kind.WEATHER,
            filename="weather.csv",
        )
        second = import_historical_csv(
            dataset=self.dataset,
            upload=BytesIO(body),
            kind=DataImportJob.Kind.WEATHER,
            filename="weather.csv",
        )
        self.assertEqual(first.status, DataImportJob.Status.COMPLETED)
        self.assertEqual(second.rows_imported, 1)
        self.assertEqual(HistoricalWeatherObservation.objects.count(), 1)
        self.dataset.refresh_from_db()
        self.assertEqual(str(self.dataset.date_start), "2025-01-01")

    def test_invalid_csv_records_failed_job_without_partial_rows(self):
        with self.assertRaises(DataImportValidationError):
            import_historical_csv(
                dataset=self.dataset,
                upload=BytesIO(b"district,rainfall_mm\nKurigram,12\n"),
                kind=DataImportJob.Kind.WEATHER,
                filename="broken.csv",
            )
        job = DataImportJob.objects.get()
        self.assertEqual(job.status, DataImportJob.Status.FAILED)
        self.assertTrue(job.errors)
        self.assertFalse(HistoricalWeatherObservation.objects.exists())

    def test_imports_crop_observation(self):
        body = b"district,crop_name,year,season,production_tonnes,yield_tonnes_per_hectare\nDinajpur,Rice,2024,Aman,125.5,3.2\n"
        job = import_historical_csv(
            dataset=self.dataset,
            upload=BytesIO(body),
            kind=DataImportJob.Kind.CROP,
            filename="crop.csv",
        )
        self.assertEqual(job.rows_imported, 1)
        self.assertEqual(HistoricalCropObservation.objects.get().crop_name, "Rice")


class PublicHistoryViewTests(TestCase):
    def test_empty_database_uses_explicit_sample_state(self):
        response = self.client.get(reverse("agricultural_data:public_history"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_demo_data"])
        self.assertContains(response, "Demonstration or unavailable series")

    def test_weather_and_crop_provenance_are_selected_and_labeled_independently(self):
        verified_source = DataSource.objects.create(
            name="Verified weather source",
            provider="Reviewed provider",
            kind=DataSource.Kind.HISTORICAL_WEATHER,
            is_demo=False,
        )
        verified_dataset = AgriculturalDataset.objects.create(
            source=verified_source,
            title="Verified weather history",
            slug="verified-weather-history",
            status=AgriculturalDataset.Status.VERIFIED,
        )
        sample_crop_source = DataSource.objects.create(
            name="Sample crop source",
            provider="Local demo",
            kind=DataSource.Kind.CROP,
            is_demo=True,
        )
        sample_crop_dataset = AgriculturalDataset.objects.create(
            source=sample_crop_source,
            title="Sample crop history",
            slug="sample-crop-history",
            status=AgriculturalDataset.Status.SAMPLE,
        )
        region = Region.objects.create(district="Kurigram")
        HistoricalWeatherObservation.objects.create(
            dataset=verified_dataset,
            region=region,
            observed_on="2025-01-01",
            rainfall_mm=48,
            temperature_mean_c=27,
        )
        HistoricalCropObservation.objects.create(
            dataset=sample_crop_dataset,
            region=region,
            crop_name="Rice",
            year=2025,
            production_tonnes=130,
        )

        response = self.client.get(reverse("agricultural_data:public_history"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["weather_is_demo"])
        self.assertTrue(response.context["crop_is_demo"])
        self.assertEqual(response.context["weather_source_meta"]["name"], "Verified weather source")
        self.assertEqual(response.context["crop_source_meta"]["name"], "Sample crop source")
        self.assertContains(response, "Crop source:</strong> Sample crop source")

    def test_stored_sample_dataset_remains_explicitly_labeled_demo(self):
        source = DataSource.objects.create(
            name="Sample source",
            provider="Local demo",
            kind=DataSource.Kind.HISTORICAL_WEATHER,
            is_demo=True,
        )
        dataset = AgriculturalDataset.objects.create(
            source=source,
            title="Sample history",
            slug="sample-history",
            status=AgriculturalDataset.Status.SAMPLE,
        )
        region = Region.objects.create(district="Kurigram")
        HistoricalWeatherObservation.objects.create(
            dataset=dataset,
            region=region,
            observed_on="2025-01-01",
            rainfall_mm=12,
        )
        response = self.client.get(reverse("agricultural_data:public_history"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_demo_data"])
        self.assertEqual(response.context["chart_data"]["rainfall"], [12.0])
        self.assertEqual(response.context["weather_source_meta"]["name"], "Sample source")
