from datetime import date, timedelta
from decimal import Decimal
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import (
    AgriculturalistProfile,
    AgriculturalistVerification,
    FarmerProfile,
    User,
)
from apps.administration.models import AuditLog
from apps.agricultural_data.models import (
    AgriculturalDataset,
    DataSource,
    HistoricalCropObservation,
    HistoricalWeatherObservation,
    Region,
)
from apps.consultations.models import (
    Consultation,
    ConsultationMessage,
    ExpertAssignment,
    ExpertRecommendation,
    FarmDataConsent,
)
from apps.core.models import SupportTicket
from apps.decisions.models import DecisionOutcome, FarmingDecision
from apps.farms.models import Crop, CropPlanting, Farm, FarmActivity, FarmTask, Field
from apps.learning.models import LearningArticle, LearningCategory
from apps.notifications.models import Notification
from apps.simulations.models import SimulationScenario
from apps.simulations.services import calculate_and_store
from apps.weather.models import WeatherAlert, WeatherForecast, WeatherObservation


DEMO_PASSWORD = "FarmDemo@2026!"


class Command(BaseCommand):
    help = "Create or refresh local-only demo accounts and clearly labeled demonstration data."

    def handle(self, *args, **options):
        settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
        if not settings.DEBUG or not settings.DEMO_MODE or not settings_module.endswith(".development"):
            raise CommandError("seed_demo is restricted to the explicit development configuration with DEBUG=True and DEMO_MODE=True.")

        with transaction.atomic():
            admin_user = self._user(
                "admin@farmtime.test",
                "System Admin",
                User.Role.ADMIN,
                district="Dhaka",
                is_staff=True,
                is_superuser=True,
            )
            operations_admin = self._user(
                "operations.admin@farmtime.test",
                "Nadia Islam",
                User.Role.ADMIN,
                district="Dhaka",
                is_staff=True,
                is_superuser=False,
            )
            expert = self._user(
                "agriculturalist@farmtime.test",
                "Dr. Ayesha Rahman",
                User.Role.AGRICULTURALIST,
                district="Kurigram",
            )
            soil_expert = self._user(
                "soil.expert@farmtime.test",
                "Dr. Farhana Akter",
                User.Role.AGRICULTURALIST,
                district="Rangpur",
            )
            farmer = self._user(
                "farmer@farmtime.test",
                "Rahim Mia",
                User.Role.FARMER,
                district="Kurigram",
                upazila="Ulipur",
            )
            salma = self._user(
                "salma.farmer@farmtime.test",
                "Salma Begum",
                User.Role.FARMER,
                district="Rangpur",
                upazila="Kaunia",
            )

            FarmerProfile.objects.update_or_create(
                user=farmer,
                defaults={"experience": FarmerProfile.Experience.SIX_TO_TEN, "preferred_area_unit": "ACRE"},
            )
            FarmerProfile.objects.update_or_create(
                user=salma,
                defaults={
                    "experience": FarmerProfile.Experience.ONE_TO_FIVE,
                    "preferred_area_unit": "ACRE",
                    "bio": "Demonstration vegetable grower testing field records and expert consultations.",
                },
            )
            expert_profile, _ = AgriculturalistProfile.objects.update_or_create(
                user=expert,
                defaults={
                    "specialization": "Crop science and climate-resilient agriculture",
                    "qualifications": "MSc in Agronomy; demonstration credentials for local development only.",
                    "organization": "Kurigram Agricultural Advisory Centre",
                    "license_number": "DEMO-AGR-2026",
                    "years_experience": 9,
                    "bio": "Supports crop planning, irrigation, and evidence-aware farm decisions.",
                    "is_approved": True,
                    "approved_at": timezone.now(),
                },
            )
            AgriculturalistVerification.objects.update_or_create(
                agriculturalist=expert_profile,
                defaults={
                    "status": AgriculturalistVerification.Status.APPROVED,
                    "reviewer": admin_user,
                    "notes": "Approved demonstration profile. Not a real professional credential.",
                    "reviewed_at": timezone.now(),
                },
            )
            soil_expert_profile, _ = AgriculturalistProfile.objects.update_or_create(
                user=soil_expert,
                defaults={
                    "specialization": "Soil health, vegetable crops, and irrigation management",
                    "qualifications": "MSc in Soil Science; demonstration credentials for local development only.",
                    "organization": "Rangpur Farm Advisory Lab",
                    "license_number": "DEMO-SOIL-2026",
                    "years_experience": 7,
                    "bio": "Supports soil-moisture checks, vegetable crop care, and practical irrigation planning.",
                    "is_approved": True,
                    "approved_at": timezone.now(),
                },
            )
            AgriculturalistVerification.objects.update_or_create(
                agriculturalist=soil_expert_profile,
                defaults={
                    "status": AgriculturalistVerification.Status.APPROVED,
                    "reviewer": operations_admin,
                    "notes": "Approved demonstration profile. Not a real professional credential.",
                    "reviewed_at": timezone.now(),
                },
            )

            region, _ = Region.objects.get_or_create(
                district="Kurigram",
                upazila="Ulipur",
                defaults={"latitude": Decimal("25.8054"), "longitude": Decimal("89.6362")},
            )
            district_region, _ = Region.objects.get_or_create(
                district="Kurigram",
                upazila="",
                defaults={"latitude": Decimal("25.8054"), "longitude": Decimal("89.6362")},
            )
            sample_source, _ = DataSource.objects.update_or_create(
                name="Farm Time Machine demonstration pack",
                defaults={
                    "provider": "Farm Time Machine local development seed",
                    "kind": DataSource.Kind.HISTORICAL_WEATHER,
                    "description": "Synthetic annual values created only to demonstrate charts and workflows.",
                    "attribution": "Demonstration data - not for agronomic decisions",
                    "geographic_coverage": "Kurigram demonstration region",
                    "update_frequency": "Fixed local sample",
                    "limitations": "Not observed weather and not suitable for real farm decisions.",
                    "is_active": True,
                    "is_demo": True,
                    "last_updated_at": timezone.now(),
                },
            )
            dataset, _ = AgriculturalDataset.objects.update_or_create(
                slug="kurigram-demonstration-history-2016-2025",
                defaults={
                    "source": sample_source,
                    "title": "Kurigram demonstration history 2016-2025",
                    "description": "Clearly labeled synthetic values for local UI and workflow testing.",
                    "status": AgriculturalDataset.Status.SAMPLE,
                    "geographic_coverage": "Kurigram",
                    "date_start": date(2016, 1, 1),
                    "date_end": date(2025, 12, 31),
                    "units": "rainfall mm; temperature °C",
                    "quality_notes": "Illustrative series. Do not interpret as observed climate history.",
                },
            )
            rainfall = [980, 1120, 870, 640, 1180, 940, 1030, 760, 910, 1090]
            temperatures = [33.4, 34.1, 34.8, 36.2, 35.1, 34.7, 35.5, 36.0, 35.2, 34.9]
            for offset, year in enumerate(range(2016, 2026)):
                HistoricalWeatherObservation.objects.update_or_create(
                    dataset=dataset,
                    region=district_region,
                    observed_on=date(year, 7, 1),
                    defaults={
                        "rainfall_mm": Decimal(rainfall[offset]),
                        "temperature_min_c": Decimal("22.0"),
                        "temperature_max_c": Decimal(str(temperatures[offset])),
                        "temperature_mean_c": Decimal("28.0"),
                        "humidity_percent": Decimal("72.0"),
                        "quality_flag": HistoricalWeatherObservation.Quality.ESTIMATED,
                        "notes": "Annual demonstration marker, not an observed daily value.",
                    },
                )
                HistoricalCropObservation.objects.update_or_create(
                    dataset=dataset,
                    region=district_region,
                    crop_name="Rice",
                    variety="Demo composite",
                    year=year,
                    season="Aman",
                    defaults={
                        "cultivated_area_hectares": Decimal(1200 + offset * 25),
                        "production_tonnes": Decimal(3100 + offset * 70),
                        "yield_tonnes_per_hectare": Decimal("2.600") + Decimal(offset) / Decimal(100),
                        "quality_notes": "Synthetic demonstration record.",
                    },
                )

            farm, _ = Farm.objects.update_or_create(
                owner=farmer,
                name="Rahim Family Farm",
                defaults={
                    "district": "Kurigram",
                    "upazila": "Ulipur",
                    "village": "Demo Village",
                    "land_area": Decimal("1.65"),
                    "area_unit": "ACRE",
                    "soil_type": "LOAM",
                    "irrigation_type": "PUMP",
                    "description": "Private demonstration farm for local development workflows.",
                    "is_archived": False,
                },
            )
            field, _ = Field.objects.update_or_create(
                farm=farm,
                name="North Field",
                defaults={
                    "area": Decimal("1.00"),
                    "area_unit": "ACRE",
                    "soil_type": "LOAM",
                    "irrigation_type": "PUMP",
                    "status": Field.Status.ACTIVE,
                    "description": "Primary demonstration field.",
                },
            )
            rice, _ = Crop.objects.get_or_create(name="Rice", variety="BRRI dhan49")
            sesame, _ = Crop.objects.get_or_create(name="Sesame", variety="BARI Til-4")
            planting, _ = CropPlanting.objects.update_or_create(
                field=field,
                crop=rice,
                planting_date=date(2026, 7, 5),
                defaults={
                    "expected_harvest_date": date(2026, 11, 18),
                    "status": CropPlanting.Status.GROWING,
                    "notes": "Demonstration crop record.",
                },
            )
            FarmActivity.objects.update_or_create(
                farm=farm,
                field=field,
                activity_type=FarmActivity.ActivityType.IRRIGATION,
                activity_date=date(2026, 10, 28),
                defaults={"planting": planting, "details": "Checked soil moisture before a short irrigation cycle."},
            )
            FarmTask.objects.update_or_create(
                farm=farm,
                title="Inspect field drainage",
                defaults={
                    "field": field,
                    "due_date": timezone.localdate() + timedelta(days=3),
                    "status": FarmTask.Status.PENDING,
                    "priority": FarmTask.Priority.HIGH,
                },
            )

            salma_farm, _ = Farm.objects.update_or_create(
                owner=salma,
                name="Salma Vegetable Farm",
                defaults={
                    "district": "Rangpur",
                    "upazila": "Kaunia",
                    "village": "Demo Riverside",
                    "land_area": Decimal("0.90"),
                    "area_unit": "ACRE",
                    "soil_type": "SILT",
                    "irrigation_type": "DRIP",
                    "description": "A second private demonstration farm focused on vegetable workflows.",
                    "is_archived": False,
                },
            )
            salma_field, _ = Field.objects.update_or_create(
                farm=salma_farm,
                name="East Vegetable Plot",
                defaults={
                    "area": Decimal("0.60"),
                    "area_unit": "ACRE",
                    "soil_type": "SILT",
                    "irrigation_type": "DRIP",
                    "status": Field.Status.ACTIVE,
                    "description": "Demonstration tomato plot with drip irrigation.",
                },
            )
            tomato, _ = Crop.objects.get_or_create(name="Tomato", variety="BARI Tomato-15")
            salma_planting, _ = CropPlanting.objects.update_or_create(
                field=salma_field,
                crop=tomato,
                planting_date=date(2026, 9, 15),
                defaults={
                    "expected_harvest_date": date(2027, 1, 15),
                    "status": CropPlanting.Status.GROWING,
                    "notes": "Demonstration vegetable crop record.",
                },
            )
            FarmActivity.objects.update_or_create(
                farm=salma_farm,
                field=salma_field,
                activity_type=FarmActivity.ActivityType.OBSERVATION,
                activity_date=date(2026, 11, 2),
                defaults={
                    "planting": salma_planting,
                    "details": "Checked leaf condition, trellis ties, and soil moisture.",
                },
            )
            FarmTask.objects.update_or_create(
                farm=salma_farm,
                title="Inspect tomato trellis and leaf health",
                defaults={
                    "field": salma_field,
                    "due_date": timezone.localdate() + timedelta(days=1),
                    "status": FarmTask.Status.IN_PROGRESS,
                    "priority": FarmTask.Priority.HIGH,
                    "notes": "Record any leaf curling and compare moisture at three points.",
                },
            )
            FarmTask.objects.update_or_create(
                farm=salma_farm,
                title="Review drip irrigation schedule",
                defaults={
                    "field": salma_field,
                    "due_date": timezone.localdate() + timedelta(days=4),
                    "status": FarmTask.Status.PENDING,
                    "priority": FarmTask.Priority.MEDIUM,
                },
            )

            scenario, _ = SimulationScenario.objects.update_or_create(
                owner=farmer,
                name="2019 rice comparison",
                defaults={
                    "farm": farm,
                    "field": field,
                    "crop": sesame,
                    "planting_date": date(2026, 6, 15),
                    "temperature_assumption": Decimal("36.2"),
                    "rainfall_assumption": Decimal("640.0"),
                    "irrigation_scenario": SimulationScenario.IrrigationScenario.LOW,
                    "historical_year": 2019,
                    "season": SimulationScenario.Season.AMAN,
                },
            )
            calculate_and_store(scenario)
            salma_scenario, _ = SimulationScenario.objects.update_or_create(
                owner=salma,
                name="Tomato dry-week comparison",
                defaults={
                    "farm": salma_farm,
                    "field": salma_field,
                    "crop": tomato,
                    "planting_date": date(2026, 9, 15),
                    "temperature_assumption": Decimal("31.0"),
                    "rainfall_assumption": Decimal("420.0"),
                    "irrigation_scenario": SimulationScenario.IrrigationScenario.MODERATE,
                    "historical_year": 2024,
                    "season": SimulationScenario.Season.RABI,
                },
            )
            calculate_and_store(salma_scenario)
            decision, _ = FarmingDecision.objects.update_or_create(
                owner=farmer,
                title="Use shorter irrigation cycles",
                decision_date=date(2026, 10, 28),
                defaults={
                    "farm": farm,
                    "field": field,
                    "planting": planting,
                    "simulation": scenario,
                    "decision_type": FarmingDecision.DecisionType.IRRIGATION,
                    "details": "Use shorter cycles after checking field moisture and drainage.",
                    "rationale": "Demonstration decision linked to a rule-based scenario.",
                    "status": FarmingDecision.Status.REVIEWED,
                },
            )
            DecisionOutcome.objects.update_or_create(
                decision=decision,
                defaults={
                    "observed_date": date(2026, 11, 2),
                    "outcome": "No visible standing water after the shorter irrigation cycle.",
                    "rating": 4,
                    "yield_impact": "Not yet known",
                },
            )
            salma_decision, _ = FarmingDecision.objects.update_or_create(
                owner=salma,
                title="Adjust the tomato drip schedule",
                decision_date=date(2026, 11, 3),
                defaults={
                    "farm": salma_farm,
                    "field": salma_field,
                    "planting": salma_planting,
                    "simulation": salma_scenario,
                    "decision_type": FarmingDecision.DecisionType.IRRIGATION,
                    "details": "Use shorter morning drip cycles while checking moisture below the surface.",
                    "rationale": "Demonstration decision based on a saved scenario and field observations.",
                    "status": FarmingDecision.Status.REVIEWED,
                },
            )
            DecisionOutcome.objects.update_or_create(
                decision=salma_decision,
                defaults={
                    "observed_date": date(2026, 11, 5),
                    "outcome": "Surface moisture remained even and no standing water was observed.",
                    "rating": 4,
                    "yield_impact": "Too early to assess",
                },
            )

            consultation, _ = Consultation.objects.update_or_create(
                farmer=farmer,
                title="Review dry-season irrigation timing",
                defaults={
                    "agriculturalist": expert,
                    "farm": farm,
                    "description": "Please review the demonstration field context and suggest what to verify before irrigation.",
                    "status": Consultation.Status.ACTIVE,
                    "priority": Consultation.Priority.NORMAL,
                },
            )
            self._assign_demo_consultation(
                consultation,
                assigned_by=admin_user,
                consent_scope=FarmDataConsent.Scope.SUMMARY,
            )
            ConsultationMessage.objects.update_or_create(
                consultation=consultation,
                sender=farmer,
                body="The topsoil has been drying faster this week. What should I check first?",
            )
            ConsultationMessage.objects.update_or_create(
                consultation=consultation,
                sender=expert,
                body="Check moisture below the surface and inspect drainage before adjusting timing. This is demonstration advice, not a field diagnosis.",
            )
            ExpertRecommendation.objects.update_or_create(
                consultation=consultation,
                agriculturalist=expert,
                title="Moisture and drainage check",
                defaults={
                    "explanation": "Inspect root-zone moisture and drainage, then use the shortest adequate irrigation cycle. Verify locally before acting.",
                    "priority": ExpertRecommendation.Priority.WATCH,
                    "status": ExpertRecommendation.Status.PUBLISHED,
                },
            )
            salma_consultation, _ = Consultation.objects.update_or_create(
                farmer=salma,
                title="Review tomato leaf curl and soil moisture",
                defaults={
                    "agriculturalist": soil_expert,
                    "farm": salma_farm,
                    "description": "Please review the demonstration plot notes and suggest safe checks before changing irrigation.",
                    "status": Consultation.Status.ACTIVE,
                    "priority": Consultation.Priority.HIGH,
                },
            )
            self._assign_demo_consultation(
                salma_consultation,
                assigned_by=operations_admin,
                consent_scope=FarmDataConsent.Scope.FULL,
            )
            ConsultationMessage.objects.update_or_create(
                consultation=salma_consultation,
                sender=salma,
                body="A few upper leaves are curling after warmer afternoons. The soil surface also dries quickly.",
            )
            ConsultationMessage.objects.update_or_create(
                consultation=salma_consultation,
                sender=soil_expert,
                body="Inspect the underside of leaves, compare root-zone moisture at several points, and avoid changing irrigation from surface appearance alone.",
            )
            ExpertRecommendation.objects.update_or_create(
                consultation=salma_consultation,
                agriculturalist=soil_expert,
                title="Leaf and root-zone moisture inspection",
                defaults={
                    "explanation": "Record leaf symptoms, inspect for insects, and check moisture below the surface before adjusting drip duration. Seek an in-person diagnosis if symptoms spread.",
                    "priority": ExpertRecommendation.Priority.HIGH,
                    "status": ExpertRecommendation.Status.PUBLISHED,
                },
            )

            category, _ = LearningCategory.objects.get_or_create(
                slug="water-management",
                defaults={"name": "Water Management", "description": "Irrigation and soil-water learning guides."},
            )
            LearningArticle.objects.update_or_create(
                slug="check-soil-moisture-before-irrigation",
                defaults={
                    "category": category,
                    "author": expert,
                    "reviewer": admin_user,
                    "title": "Check soil moisture before irrigation",
                    "summary": "A practical demonstration guide to inspecting moisture and avoiding unnecessary irrigation.",
                    "body": "Check moisture below the dry surface, compare several field points, and inspect drainage. Consider crop stage and verified local weather. Seek qualified local advice for high-risk decisions.",
                    "language": LearningArticle.Language.ENGLISH,
                    "status": LearningArticle.Status.PUBLISHED,
                    "published_at": timezone.now(),
                },
            )
            soil_category, _ = LearningCategory.objects.get_or_create(
                slug="soil-and-vegetable-care",
                defaults={
                    "name": "Soil and Vegetable Care",
                    "description": "Practical soil checks and vegetable crop observation guides.",
                },
            )
            LearningArticle.objects.update_or_create(
                slug="inspect-root-zone-moisture-not-only-the-surface",
                defaults={
                    "category": soil_category,
                    "author": soil_expert,
                    "reviewer": operations_admin,
                    "title": "Inspect root-zone moisture, not only the surface",
                    "summary": "A demonstration guide for comparing surface dryness with moisture near crop roots.",
                    "body": "Check several points at root depth, note recent irrigation and rainfall, and record crop symptoms before changing a schedule. Verify important decisions with qualified local advice.",
                    "language": LearningArticle.Language.ENGLISH,
                    "status": LearningArticle.Status.PUBLISHED,
                    "published_at": timezone.now(),
                },
            )

            WeatherObservation.objects.filter(
                region=region,
                source=sample_source,
                raw_payload__demo=True,
            ).delete()
            WeatherObservation.objects.create(
                region=region,
                source=sample_source,
                observed_at=timezone.now().replace(minute=0, second=0, microsecond=0),
                temperature_c=Decimal("28.0"),
                humidity_percent=Decimal("72.0"),
                rainfall_mm=Decimal("0.0"),
                wind_speed_kmh=Decimal("9.0"),
                condition="Demonstration sample - not live",
                raw_payload={"demo": True},
            )
            WeatherForecast.objects.filter(
                region=region,
                source=sample_source,
                condition="Demonstration forecast",
            ).delete()
            for day_offset, max_temp in enumerate([29, 30, 31, 30, 28, 29, 28]):
                WeatherForecast.objects.create(
                    region=region,
                    source=sample_source,
                    forecast_for=timezone.localdate() + timedelta(days=day_offset),
                    issued_at=timezone.now().replace(minute=0, second=0, microsecond=0),
                    temperature_min_c=Decimal("22.0"),
                    temperature_max_c=Decimal(max_temp),
                    precipitation_probability=35 + day_offset,
                    rainfall_mm=Decimal("1.5"),
                    condition="Demonstration forecast",
                )
            WeatherAlert.objects.update_or_create(
                region=region,
                source=sample_source,
                title="Demonstration soil moisture watch",
                defaults={
                    "description": "A local-development alert used to demonstrate the notification and weather interfaces.",
                    "recommendation": "Verify current official weather and inspect field moisture before acting.",
                    "severity": WeatherAlert.Severity.WATCH,
                    "starts_at": timezone.now() - timedelta(hours=2),
                    "ends_at": timezone.now() + timedelta(days=2),
                    "is_active": True,
                },
            )

            SupportTicket.objects.update_or_create(
                user=farmer,
                subject="How do I update a field area?",
                defaults={
                    "name": farmer.display_name,
                    "email": farmer.email,
                    "message": "Demonstration support ticket for the local admin workflow.",
                    "status": SupportTicket.Status.IN_PROGRESS,
                    "priority": SupportTicket.Priority.NORMAL,
                    "staff_response": "Open My Farm, choose the field, and select Edit field.",
                },
            )
            SupportTicket.objects.update_or_create(
                user=salma,
                subject="Where can I review expert recommendations?",
                defaults={
                    "name": salma.display_name,
                    "email": salma.email,
                    "message": "Second demonstration support ticket for the local admin workflow.",
                    "status": SupportTicket.Status.OPEN,
                    "priority": SupportTicket.Priority.NORMAL,
                    "staff_response": "",
                },
            )
            self._notification(farmer, Notification.Kind.EXPERT_REPLIED, "Agriculturalist replied", "Your irrigation consultation has a new response.", f"/farmer/consultations/{consultation.pk}/")
            self._notification(expert, Notification.Kind.CONSULTATION_ASSIGNED, "Consultation assigned", "Rahim Mia shared a demonstration consultation.", f"/agriculturalist/questions/{consultation.pk}/")
            self._notification(admin_user, Notification.Kind.SYSTEM, "Demo data ready", "Local demonstration records were refreshed.", "/platform-admin/dashboard/")
            self._notification(salma, Notification.Kind.EXPERT_REPLIED, "Soil expert replied", "Your tomato consultation has a new response.", f"/farmer/consultations/{salma_consultation.pk}/")
            self._notification(soil_expert, Notification.Kind.CONSULTATION_ASSIGNED, "Consultation assigned", "Salma Begum shared a demonstration consultation.", f"/agriculturalist/questions/{salma_consultation.pk}/")
            self._notification(operations_admin, Notification.Kind.SYSTEM, "Demo operations ready", "Additional local demonstration records were refreshed.", "/platform-admin/dashboard/")
            AuditLog.objects.get_or_create(
                actor=admin_user,
                action="demo.seed_refreshed",
                target_type="Platform",
                target_identifier="local-development",
                defaults={"result": AuditLog.Result.SUCCESS, "metadata": {"demo": True}},
            )

        self.stdout.write(self.style.SUCCESS("Demo accounts and labeled sample data are ready."))
        self.stdout.write("Admins: admin@farmtime.test, operations.admin@farmtime.test")
        self.stdout.write("Agriculturalists: agriculturalist@farmtime.test, soil.expert@farmtime.test")
        self.stdout.write("Farmers: farmer@farmtime.test, salma.farmer@farmtime.test")
        self.stdout.write("All local demo accounts use the password documented in README_DEMO.md. Never reuse it outside development.")

    def _user(self, email, full_name, role, **extra):
        user, _ = User.objects.get_or_create(email=email, defaults={"full_name": full_name, "role": role})
        user.full_name = full_name
        user.role = role
        user.is_verified = True
        user.is_active = True
        user.is_staff = extra.pop("is_staff", role == User.Role.ADMIN)
        user.is_superuser = extra.pop("is_superuser", role == User.Role.ADMIN)
        for field, value in extra.items():
            setattr(user, field, value)
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _assign_demo_consultation(self, consultation, *, assigned_by, consent_scope):
        ExpertAssignment.objects.update_or_create(
            consultation=consultation,
            defaults={
                "farmer": consultation.farmer,
                "agriculturalist": consultation.agriculturalist,
                "assigned_by": assigned_by,
                "is_active": True,
                "ended_at": None,
            },
        )
        consent, _ = FarmDataConsent.objects.update_or_create(
            consultation=consultation,
            defaults={
                "farmer": consultation.farmer,
                "agriculturalist": consultation.agriculturalist,
                "farm": consultation.farm,
                "scope": consent_scope,
                "revoked_at": None,
            },
        )
        consent.full_clean()
        consent.save()

    def _notification(self, user, kind, title, body, target_url):
        Notification.objects.get_or_create(
            user=user,
            kind=kind,
            title=title,
            defaults={"body": body, "target_url": target_url},
        )
