from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import AgriculturalistProfile, User
from apps.consultations.models import Consultation, ExpertAssignment, FarmDataConsent
from apps.farms.models import Farm, FarmTask
from apps.notifications.models import Notification
from apps.simulations.models import SimulationScenario
from apps.weather.models import WeatherForecast, WeatherObservation


class SeedDemoCommandTests(TestCase):
    demo_emails = {
        "admin@farmtime.test",
        "operations.admin@farmtime.test",
        "agriculturalist@farmtime.test",
        "soil.expert@farmtime.test",
        "farmer@farmtime.test",
        "salma.farmer@farmtime.test",
    }

    @override_settings(DEBUG=True, DEMO_MODE=True)
    def test_seed_demo_is_idempotent(self):
        call_command("seed_demo", verbosity=0)
        first_counts = {
            "users": User.objects.filter(email__in=self.demo_emails).count(),
            "farms": Farm.objects.count(),
            "tasks": FarmTask.objects.count(),
            "scenarios": SimulationScenario.objects.count(),
            "consultations": Consultation.objects.count(),
            "assignments": ExpertAssignment.objects.count(),
            "consents": FarmDataConsent.objects.count(),
            "notifications": Notification.objects.count(),
        }
        call_command("seed_demo", verbosity=0)

        users = User.objects.filter(email__in=self.demo_emails)
        self.assertEqual(set(users.values_list("email", flat=True)), self.demo_emails)
        self.assertEqual(users.filter(role=User.Role.ADMIN).count(), 2)
        self.assertEqual(users.filter(role=User.Role.AGRICULTURALIST).count(), 2)
        self.assertEqual(users.filter(role=User.Role.FARMER).count(), 2)
        self.assertEqual(users.filter(is_verified=True).count(), 6)
        self.assertEqual(
            AgriculturalistProfile.objects.filter(user__email__in=self.demo_emails, is_approved=True).count(),
            2,
        )
        self.assertEqual(Farm.objects.filter(owner__email="farmer@farmtime.test", name="Rahim Family Farm").count(), 1)
        self.assertEqual(Farm.objects.filter(owner__email="salma.farmer@farmtime.test", name="Salma Vegetable Farm").count(), 1)
        self.assertTrue(User.objects.get(email="farmer@farmtime.test").check_password("FarmDemo@2026!"))
        self.assertTrue(User.objects.get(email="salma.farmer@farmtime.test").check_password("FarmDemo@2026!"))
        self.assertEqual(FarmTask.objects.filter(title="Inspect field drainage").count(), 1)
        self.assertEqual(FarmTask.objects.filter(farm__owner__email="salma.farmer@farmtime.test").count(), 2)
        salma_scenario = SimulationScenario.objects.get(
            owner__email="salma.farmer@farmtime.test",
            name="Tomato dry-week comparison",
        )
        self.assertIsNotNone(salma_scenario.result)
        salma_consultation = Consultation.objects.get(
            farmer__email="salma.farmer@farmtime.test",
            title="Review tomato leaf curl and soil moisture",
        )
        self.assertEqual(salma_consultation.agriculturalist.email, "soil.expert@farmtime.test")
        self.assertEqual(salma_consultation.data_consent.scope, FarmDataConsent.Scope.FULL)
        self.assertTrue(salma_consultation.assignment.is_active)
        self.assertEqual(WeatherObservation.objects.filter(raw_payload__demo=True).count(), 1)
        self.assertEqual(WeatherForecast.objects.filter(condition="Demonstration forecast").count(), 7)
        self.assertEqual(
            {
                "users": User.objects.filter(email__in=self.demo_emails).count(),
                "farms": Farm.objects.count(),
                "tasks": FarmTask.objects.count(),
                "scenarios": SimulationScenario.objects.count(),
                "consultations": Consultation.objects.count(),
                "assignments": ExpertAssignment.objects.count(),
                "consents": FarmDataConsent.objects.count(),
                "notifications": Notification.objects.count(),
            },
            first_counts,
        )
