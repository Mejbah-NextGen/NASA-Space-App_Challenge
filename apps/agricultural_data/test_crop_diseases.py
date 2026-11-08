from io import StringIO
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from apps.agricultural_data.management.commands.import_crop_diseases import (
    DATASET_SLUG,
    SOURCE_NAME,
    normalize_guidance_category,
)
from apps.agricultural_data.models import (
    AgriculturalDataset,
    CropDisease,
    DataImportJob,
    DataSource,
    DiseaseGuidance,
)


SAMPLE_CSV = """Crop,Disease,Information Type,Information
Rice,Blast,Symptoms,<script>alert(1)</script> lesions appear on leaves.
Rice,Blast,Symptoms,<script>alert(1)</script> lesions appear on leaves.
Rice,Blast,Chemical Control,Confirm any product and dose with a local agriculturalist.
Tomato,Wilt,Biological Control,Consider locally reviewed biological options.
"""


class CropDiseaseImportCommandTests(TestCase):
    def _csv_path(self, content=SAMPLE_CSV):
        path = Path(settings.BASE_DIR) / "tmp" / f"crop-health-{uuid4().hex}.csv"
        path.write_text(content, encoding="utf-8")
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_import_is_idempotent_deduplicated_and_provenance_labelled(self):
        path = self._csv_path()
        first_output = StringIO()
        call_command("import_crop_diseases", str(path), stdout=first_output)

        source = DataSource.objects.get(name=SOURCE_NAME)
        dataset = AgriculturalDataset.objects.get(slug=DATASET_SLUG)
        self.assertEqual(source.kind, DataSource.Kind.DISEASE)
        self.assertTrue(source.is_demo)
        self.assertIn("not a NASA dataset", source.attribution)
        self.assertEqual(dataset.status, AgriculturalDataset.Status.SAMPLE)
        self.assertEqual(CropDisease.objects.count(), 2)
        self.assertEqual(DiseaseGuidance.objects.count(), 3)
        self.assertEqual(dataset.metadata["rows_received"], 4)
        self.assertEqual(dataset.metadata["unique_guidance_rows"], 3)
        self.assertEqual(dataset.metadata["duplicate_rows_skipped"], 1)
        self.assertEqual(DataImportJob.objects.get().kind, DataImportJob.Kind.DISEASE)
        self.assertIn("SAMPLE/unverified", first_output.getvalue())

        second_output = StringIO()
        call_command("import_crop_diseases", str(path), stdout=second_output)
        self.assertEqual(CropDisease.objects.count(), 2)
        self.assertEqual(DiseaseGuidance.objects.count(), 3)
        self.assertEqual(DataImportJob.objects.count(), 2)
        self.assertIn("created 0 guidance entries", second_output.getvalue())

    def test_validation_failure_is_atomic(self):
        path = self._csv_path(
            "Crop,Disease,Information Type,Information\n"
            "Rice,Blast,Symptoms,Leaf lesions\n"
            "Rice,,Prevention,Remove infected debris\n"
        )
        with self.assertRaisesMessage(CommandError, "blank required values"):
            call_command("import_crop_diseases", str(path))
        self.assertFalse(DataSource.objects.filter(name=SOURCE_NAME).exists())
        self.assertFalse(CropDisease.objects.exists())
        self.assertFalse(DataImportJob.objects.exists())

    def test_missing_required_column_is_rejected(self):
        path = self._csv_path("Crop,Disease,Information\nRice,Blast,Leaf lesions\n")
        with self.assertRaisesMessage(CommandError, "information type"):
            call_command("import_crop_diseases", str(path))

    def test_category_normalization_is_ordered_and_deterministic(self):
        self.assertEqual(normalize_guidance_category("Symptoms"), DiseaseGuidance.Category.IDENTIFICATION)
        self.assertEqual(
            normalize_guidance_category("Biological Control Implementation"),
            DiseaseGuidance.Category.BIOLOGICAL,
        )
        self.assertEqual(normalize_guidance_category("Fungicide Application"), DiseaseGuidance.Category.TREATMENT)
        self.assertEqual(normalize_guidance_category("Orchard Sanitation"), DiseaseGuidance.Category.PREVENTION)
        self.assertEqual(normalize_guidance_category("Disease Cycle"), DiseaseGuidance.Category.BIOLOGY)
        self.assertEqual(normalize_guidance_category("Yield Loss"), DiseaseGuidance.Category.IMPACT)
        self.assertEqual(normalize_guidance_category("General Information"), DiseaseGuidance.Category.OTHER)


class BundledCropDiseaseDatasetTests(TestCase):
    def test_bundled_dataset_imports_with_audited_counts_and_checksum(self):
        path = Path(settings.BASE_DIR) / "fixtures" / "crop_disease_treatment.csv"
        call_command("import_crop_diseases", str(path), stdout=StringIO())
        dataset = AgriculturalDataset.objects.get(slug=DATASET_SLUG)
        self.assertEqual(dataset.metadata["sha256"], "9B12C2CCC7F5FF87FF9681B963383A3B4F07174275DAF1FEF432FCA1CF41CCF2")
        self.assertEqual(dataset.metadata["rows_received"], 3110)
        self.assertEqual(dataset.metadata["duplicate_rows_skipped"], 63)
        self.assertEqual(dataset.metadata["crop_count"], 42)
        self.assertEqual(CropDisease.objects.count(), 858)
        self.assertEqual(DiseaseGuidance.objects.count(), 3047)


class CropHealthViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.csv_path = Path(settings.BASE_DIR) / "tmp" / f"crop-health-{uuid4().hex}.csv"
        cls.csv_path.write_text(SAMPLE_CSV, encoding="utf-8")
        call_command("import_crop_diseases", str(cls.csv_path), stdout=StringIO())

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls.csv_path.unlink(missing_ok=True)

    def test_page_exposes_summary_charts_and_unverified_warning(self):
        response = self.client.get(reverse("agricultural_data:crop_health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["library_summary"], {"crops": 2, "diseases": 2, "guidance": 3})
        self.assertEqual(response.context["crop_chart"]["labels"], ["Rice", "Tomato"])
        self.assertContains(response, "Sample, unverified guidance")
        self.assertContains(response, "not NASA data")
        self.assertContains(response, "Crop disease guidance reference")

    def test_crop_and_category_filters_limit_visible_guidance(self):
        response = self.client.get(
            reverse("agricultural_data:crop_health"),
            {"crop": "Rice", "category": DiseaseGuidance.Category.TREATMENT},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 1)
        disease = response.context["diseases"][0]
        self.assertEqual(disease.crop_name, "Rice")
        self.assertEqual(len(disease.visible_guidance), 1)
        self.assertEqual(disease.visible_guidance[0].category, DiseaseGuidance.Category.TREATMENT)
        self.assertContains(response, "Verify locally")

    def test_search_content_is_escaped(self):
        response = self.client.get(reverse("agricultural_data:crop_health"), {"q": "script"})
        self.assertEqual(response.context["paginator"].count, 1)
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_search_and_category_must_match_the_same_visible_guidance(self):
        response = self.client.get(
            reverse("agricultural_data:crop_health"),
            {"q": "script", "category": DiseaseGuidance.Category.TREATMENT},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 0)
        self.assertContains(response, "No guidance matches these filters")

    def test_results_are_paginated(self):
        dataset = AgriculturalDataset.objects.get(slug=DATASET_SLUG)
        for index in range(13):
            disease = CropDisease.objects.create(
                dataset=dataset,
                crop_name="Maize",
                disease_name=f"Demonstration disease {index:02d}",
            )
            DiseaseGuidance.objects.create(
                disease=disease,
                information_type="Symptoms",
                category=DiseaseGuidance.Category.IDENTIFICATION,
                content=f"Demonstration symptom {index}",
                content_hash=f"{index:064x}",
            )
        response = self.client.get(reverse("agricultural_data:crop_health"))
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["diseases"]), 12)
        self.assertContains(response, "Next")


class EmptyCropHealthViewTests(TestCase):
    def test_empty_library_has_actionable_import_state(self):
        response = self.client.get(reverse("agricultural_data:crop_health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["library_summary"]["guidance"], 0)
        self.assertContains(response, "The crop-health dataset has not been imported")
        self.assertContains(response, "import_crop_diseases")
