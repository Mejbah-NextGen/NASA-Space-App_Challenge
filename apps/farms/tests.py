from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

from .models import AreaUnit, Farm, Field, IrrigationType, SoilType


class FarmOwnershipTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="Testpass123!", full_name="Owner", role=User.Role.FARMER, is_verified=True)
        self.other = User.objects.create_user(email="other@example.com", password="Testpass123!", full_name="Other", role=User.Role.FARMER, is_verified=True)
        self.farm = Farm.objects.create(
            owner=self.owner, name="North Farm", district="Kurigram", land_area=Decimal("2.00"),
            area_unit=AreaUnit.ACRE, soil_type=SoilType.LOAM, irrigation_type=IrrigationType.RAINFED,
        )

    def test_other_farmer_cannot_view_farm(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("farms:farm_detail", args=[self.farm.pk]))
        self.assertEqual(response.status_code, 404)

    def test_archive_requires_post_and_owner(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("farms:farm_archive", args=[self.farm.pk])).status_code, 405)
        response = self.client.post(reverse("farms:farm_archive", args=[self.farm.pk]))
        self.assertRedirects(response, reverse("farms:farm_list"))
        self.farm.refresh_from_db()
        self.assertTrue(self.farm.is_archived)

    def test_field_cannot_exceed_farm_in_same_unit(self):
        field = Field(
            farm=self.farm, name="Oversized", area=Decimal("3.00"), area_unit=AreaUnit.ACRE,
            soil_type=SoilType.LOAM, irrigation_type=IrrigationType.RAINFED,
        )
        with self.assertRaises(ValidationError):
            field.full_clean()

