from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .services import get_weather


class WeatherServiceTests(SimpleTestCase):
    def tearDown(self):
        cache.clear()

    @override_settings(WEATHER_LIVE_ENABLED=False, DEMO_MODE=True)
    def test_disabled_live_service_returns_explicit_demo_label(self):
        result = get_weather("Kurigram")
        self.assertTrue(result["is_demo"])
        self.assertIn("DEMONSTRATION", result["status_label"])
        self.assertTrue(result["fallback_reason"])

    @override_settings(WEATHER_LIVE_ENABLED=True, DEMO_MODE=False)
    @patch("apps.weather.services.requests.get")
    def test_maps_open_meteo_response(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "timezone": "Asia/Dhaka",
            "current": {
                "time": "2026-11-06T09:00",
                "temperature_2m": 27.4,
                "relative_humidity_2m": 68,
                "rain": 0,
                "weather_code": 2,
                "wind_speed_10m": 8.2,
            },
            "daily": {
                "time": ["2026-11-06"],
                "weather_code": [2],
                "temperature_2m_max": [30],
                "temperature_2m_min": [22],
                "precipitation_sum": [1.2],
                "precipitation_probability_max": [35],
            },
        }
        mock_get.return_value = response
        result = get_weather("Kurigram")
        self.assertFalse(result["is_demo"])
        self.assertEqual(result["source"], "Open-Meteo")
        self.assertEqual(result["condition"], "Partly cloudy")
        self.assertEqual(len(result["forecast"]), 1)
        mock_get.assert_called_once()

    @override_settings(WEATHER_LIVE_ENABLED=True, DEMO_MODE=False)
    @patch("apps.weather.services.requests.get", side_effect=requests.Timeout("network down"))
    def test_provider_failure_returns_clear_unavailable_state(self, mock_get):
        result = get_weather("Kurigram")
        self.assertFalse(result["available"])
        self.assertEqual(result["status_label"], "LIVE DATA UNAVAILABLE")
        self.assertNotIn("network down", result["error"])


@override_settings(WEATHER_LIVE_ENABLED=False, DEMO_MODE=True)
class WeatherViewTests(TestCase):
    def test_public_weather_page_labels_demo_values(self):
        response = self.client.get(reverse("weather:public_weather"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DEMONSTRATION DATA")
