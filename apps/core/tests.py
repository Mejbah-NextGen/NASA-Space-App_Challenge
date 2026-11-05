from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

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
    def test_home_renders_public_weather_and_history(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Understand the Past")
        self.assertContains(response, "DEMONSTRATION DATA")

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
