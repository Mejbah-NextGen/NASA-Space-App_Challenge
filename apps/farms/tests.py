from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

from .models import AreaUnit, Farm, FarmActivity, Field, IrrigationType, SoilType


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

    def test_verified_farmer_can_create_update_field_and_record_activity(self):
        self.client.force_login(self.owner)
        create = self.client.post(
            reverse("farms:farm_create"),
            {
                "name": "River Farm",
                "district": "Kurigram",
                "upazila": "Ulipur",
                "village": "River Village",
                "land_area": "3.00",
                "area_unit": AreaUnit.ACRE,
                "soil_type": SoilType.LOAM,
                "irrigation_type": IrrigationType.RAINFED,
                "description": "Workflow test farm.",
            },
        )
        created_farm = Farm.objects.get(owner=self.owner, name="River Farm")
        self.assertRedirects(create, reverse("farms:farm_detail", args=[created_farm.pk]))

        update = self.client.post(
            reverse("farms:farm_update", args=[created_farm.pk]),
            {
                "name": "River Farm Updated",
                "district": "Kurigram",
                "upazila": "Ulipur",
                "village": "River Village",
                "land_area": "3.00",
                "area_unit": AreaUnit.ACRE,
                "soil_type": SoilType.LOAM,
                "irrigation_type": IrrigationType.RAINFED,
                "description": "Updated workflow test farm.",
            },
        )
        self.assertRedirects(update, reverse("farms:farm_detail", args=[created_farm.pk]))
        created_farm.refresh_from_db()
        self.assertEqual(created_farm.name, "River Farm Updated")

        field_response = self.client.post(
            reverse("farms:field_create", args=[created_farm.pk]),
            {
                "name": "East Field",
                "area": "1.25",
                "area_unit": AreaUnit.ACRE,
                "soil_type": SoilType.LOAM,
                "irrigation_type": IrrigationType.RAINFED,
                "status": Field.Status.ACTIVE,
                "description": "Field workflow record.",
            },
        )
        self.assertRedirects(field_response, reverse("farms:farm_detail", args=[created_farm.pk]))
        field = Field.objects.get(farm=created_farm, name="East Field")

        activity_response = self.client.post(
            reverse("farms:activity_create", args=[created_farm.pk]),
            {
                "field": field.pk,
                "planting": "",
                "activity_type": FarmActivity.ActivityType.IRRIGATION,
                "activity_date": date(2026, 11, 6),
                "details": "Checked soil moisture and irrigated briefly.",
                "cost": "150.00",
            },
        )
        self.assertRedirects(activity_response, reverse("farms:farm_detail", args=[created_farm.pk]))
        self.assertTrue(FarmActivity.objects.filter(farm=created_farm, field=field).exists())

