from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.farms.models import AreaUnit, Farm, IrrigationType, SoilType

from .models import FarmingDecision


class DecisionPrivacyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="Testpass123!", full_name="Owner", role=User.Role.FARMER, is_verified=True)
        self.other = User.objects.create_user(email="other@example.com", password="Testpass123!", full_name="Other", role=User.Role.FARMER, is_verified=True)
        farm = Farm.objects.create(owner=self.owner, name="Decision Farm", district="Dinajpur", land_area=1, area_unit=AreaUnit.ACRE, soil_type=SoilType.LOAM, irrigation_type=IrrigationType.RAINFED)
        self.decision = FarmingDecision.objects.create(
            owner=self.owner, farm=farm, decision_type=FarmingDecision.DecisionType.PLANTING,
            title="Plant sesame", decision_date=date(2026, 4, 1), details="Selected a lower-water crop.", status=FarmingDecision.Status.COMPLETED,
        )

    def test_owner_can_view_decision(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("decisions:detail", args=[self.decision.pk])).status_code, 200)

    def test_other_farmer_cannot_view_decision(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("decisions:detail", args=[self.decision.pk])).status_code, 404)

