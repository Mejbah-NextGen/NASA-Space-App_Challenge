from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.farms.models import AreaUnit, Crop, Farm, IrrigationType, SoilType

from .models import SimulationScenario
from .services import calculate_and_store, run_baseline


class SimulationBaselineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="farmer@example.com", password="Testpass123!", full_name="Farmer", role=User.Role.FARMER, is_verified=True)
        self.other = User.objects.create_user(email="other@example.com", password="Testpass123!", full_name="Other", role=User.Role.FARMER, is_verified=True)
        self.farm = Farm.objects.create(owner=self.user, name="Demo Farm", district="Rangpur", land_area=1, area_unit=AreaUnit.ACRE, soil_type=SoilType.LOAM, irrigation_type=IrrigationType.PUMP)
        self.crop = Crop.objects.create(name="Rice", variety="BRRI dhan28")
        self.scenario = SimulationScenario.objects.create(
            owner=self.user, farm=self.farm, crop=self.crop, name="Dry rice test", planting_date=date(2026, 1, 10),
            temperature_assumption=Decimal("31.0"), rainfall_assumption=Decimal("500.0"),
            irrigation_scenario=SimulationScenario.IrrigationScenario.LOW, historical_year=2024,
            season=SimulationScenario.Season.BORO,
        )

    def test_baseline_is_deterministic_and_bounded(self):
        first = run_baseline(self.scenario)
        second = run_baseline(self.scenario)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first.estimated_suitability, 0)
        self.assertLessEqual(first.estimated_suitability, 100)

    def test_result_is_persisted_with_disclaimer(self):
        result = calculate_and_store(self.scenario)
        self.assertIn("not a yield forecast", result.disclaimer)
        self.assertEqual(result.input_snapshot["crop"], "Rice")

    def test_other_farmer_cannot_view_result(self):
        calculate_and_store(self.scenario)
        self.client.force_login(self.other)
        response = self.client.get(reverse("simulations:detail", args=[self.scenario.pk]))
        self.assertEqual(response.status_code, 404)

