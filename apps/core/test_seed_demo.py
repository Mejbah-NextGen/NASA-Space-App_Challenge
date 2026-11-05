from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.farms.models import Farm, FarmTask
from apps.weather.models import WeatherForecast, WeatherObservation


class SeedDemoCommandTests(TestCase):
    @override_settings(DEBUG=True, DEMO_MODE=True)
    def test_seed_demo_is_idempotent(self):
        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)
        self.assertEqual(User.objects.filter(email__in=[
            "admin@farmtime.test",
            "agriculturalist@farmtime.test",
            "farmer@farmtime.test",
        ]).count(), 3)
        self.assertEqual(Farm.objects.filter(owner__email="farmer@farmtime.test", name="Rahim Family Farm").count(), 1)
        self.assertTrue(User.objects.get(email="farmer@farmtime.test").check_password("FarmDemo@2026!"))
        self.assertEqual(FarmTask.objects.filter(title="Inspect field drainage").count(), 1)
        self.assertEqual(WeatherObservation.objects.filter(raw_payload__demo=True).count(), 1)
        self.assertEqual(WeatherForecast.objects.filter(condition="Demonstration forecast").count(), 7)
