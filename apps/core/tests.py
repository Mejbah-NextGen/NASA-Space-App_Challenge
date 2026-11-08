from datetime import date

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.agricultural_data.models import (
    AgriculturalDataset,
    CropDisease,
    DataSource,
    DiseaseGuidance,
    HistoricalWeatherObservation,
    Region,
)

from .forms import SupportTicketForm


class SupportTicketFormTests(TestCase):
    def test_rejects_unhelpfully_short_message(self):
        form = SupportTicketForm(
            data={"name": "Rahim", "email": "rahim@example.com", "subject": "Help", "message": "Too short"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("message", form.errors)

    def test_accepts_valid_support_request(self):
        form = SupportTicketForm(
            data={
                "name": "Rahim",
                "email": "rahim@example.com",
                "subject": "Weather card",
                "message": "The weather card has not updated since yesterday.",
            }
        )
        self.assertTrue(form.is_valid())


@override_settings(WEATHER_LIVE_ENABLED=False, DEMO_MODE=True)
class PublicPageSmokeTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_home_renders_public_weather_and_history(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Understand the Past")
        self.assertContains(response, "DEMONSTRATION DATA")
        self.assertIn("default-src 'self'", response["Content-Security-Policy"])
        self.assertEqual(response["Permissions-Policy"], "camera=(), geolocation=(), microphone=()")

    def test_home_does_not_mix_verified_and_demo_weather_history(self):
        region = Region.objects.create(district="Kurigram", upazila="Ulipur")
        verified_source = DataSource.objects.create(
            name="Verified history source",
            provider="Test provider",
            kind=DataSource.Kind.HISTORICAL_WEATHER,
            is_demo=False,
        )
        sample_source = DataSource.objects.create(
            name="Sample history source",
            provider="Test provider",
            kind=DataSource.Kind.HISTORICAL_WEATHER,
            is_demo=True,
        )
        verified_dataset = AgriculturalDataset.objects.create(
            source=verified_source,
            title="Verified weather",
            slug="verified-weather",
            status=AgriculturalDataset.Status.VERIFIED,
        )
        sample_dataset = AgriculturalDataset.objects.create(
            source=sample_source,
            title="Sample weather",
            slug="sample-weather",
            status=AgriculturalDataset.Status.SAMPLE,
        )
        HistoricalWeatherObservation.objects.create(
            dataset=verified_dataset,
            region=region,
            observed_on=date(2025, 6, 1),
            rainfall_mm="100.00",
        )
        HistoricalWeatherObservation.objects.create(
            dataset=sample_dataset,
            region=region,
            observed_on=date(2025, 6, 2),
            rainfall_mm="900.00",
        )

        response = self.client.get(reverse("core:home"), {"district": "Kurigram"})

        self.assertEqual(response.context["history_chart"]["rainfall"], [100.0])
        self.assertFalse(response.context["history_is_demo"])

    def test_home_renders_crop_health_visualization_and_nasa_news(self):
        source = DataSource.objects.create(
            name="Contributor disease test",
            provider="Test contributor",
            kind=DataSource.Kind.DISEASE,
            is_active=True,
            is_demo=True,
        )
        dataset = AgriculturalDataset.objects.create(
            source=source,
            title="Disease test data",
            slug="disease-test-data",
            status=AgriculturalDataset.Status.SAMPLE,
        )
        disease = CropDisease.objects.create(dataset=dataset, crop_name="Rice", disease_name="Blast")
        DiseaseGuidance.objects.create(
            disease=disease,
            information_type="Symptoms",
            category=DiseaseGuidance.Category.IDENTIFICATION,
            content="Demonstration symptom reference.",
            content_hash="a" * 64,
        )

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crop Health Library")
        self.assertContains(response, "home-crop-disease-data")
        self.assertContains(response, "NASA agriculture updates")
        self.assertContains(response, "NISAR will map farmland")

    def test_help_creates_ticket(self):
        response = self.client.post(
            reverse("core:help"),
            {
                "name": "Rahim",
                "email": "rahim@example.com",
                "subject": "Historical chart",
                "message": "I need help understanding the historical rainfall chart.",
            },
        )
        self.assertRedirects(response, reverse("core:help"))

    @override_settings(SUPPORT_RATE_LIMIT_PER_10_MINUTES=1)
    def test_public_support_submission_is_rate_limited(self):
        payload = {
            "name": "Rahim",
            "email": "rahim@example.com",
            "subject": "Weather card",
            "message": "The weather card has not updated since yesterday.",
        }
        self.assertEqual(self.client.post(reverse("core:help"), payload).status_code, 302)
        blocked = self.client.post(reverse("core:help"), payload)
        self.assertEqual(blocked.status_code, 429)
        self.assertContains(blocked, "Too many support requests", status_code=429)

    def test_standard_language_switch_persists_bengali_public_copy(self):
        english = self.client.get(reverse("core:home"))
        self.assertContains(english, "Understand the Past.")
        response = self.client.post(
            reverse("set_language"),
            {"language": "bn", "next": reverse("core:home")},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, "bn")
        self.assertEqual(response.wsgi_request.LANGUAGE_CODE, "bn")
        self.assertContains(response, "অতীতকে বুঝুন।")
        self.assertContains(response, "খামারের ইতিহাস দেখুন")
        self.assertContains(response, "আবহাওয়া")
