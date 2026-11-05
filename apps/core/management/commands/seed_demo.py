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
    ExpertRecommendation,
    FarmDataConsent,
)
from apps.consultations.services import assign_consultation
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
            expert = self._user(
                "agriculturalist@farmtime.test",
                "Dr. Ayesha Rahman",
                User.Role.AGRICULTURALIST,
                district="Kurigram",
            )
            farmer = self._user(
                "farmer@farmtime.test",
                "Rahim Mia",
                User.Role.FARMER,
                district="Kurigram",
                upazila="Ulipur",
            )

            FarmerProfile.objects.update_or_create(
                user=farmer,
                defaults={"experience": FarmerProfile.Experience.SIX_TO_TEN, "preferred_area_unit": "ACRE"},
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
            assign_consultation(consultation, assigned_by=admin_user, share_farm=True, consent_scope=FarmDataConsent.Scope.SUMMARY)
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
            self._notification(farmer, Notification.Kind.EXPERT_REPLIED, "Agriculturalist replied", "Your irrigation consultation has a new response.", f"/farmer/consultations/{consultation.pk}/")
            self._notification(expert, Notification.Kind.CONSULTATION_ASSIGNED, "Consultation assigned", "Rahim Mia shared a demonstration consultation.", f"/agriculturalist/questions/{consultation.pk}/")
            self._notification(admin_user, Notification.Kind.SYSTEM, "Demo data ready", "Local demonstration records were refreshed.", "/platform-admin/dashboard/")
            AuditLog.objects.get_or_create(
                actor=admin_user,
                action="demo.seed_refreshed",
                target_type="Platform",
                target_identifier="local-development",
                defaults={"result": AuditLog.Result.SUCCESS, "metadata": {"demo": True}},
            )

        self.stdout.write(self.style.SUCCESS("Demo accounts and labeled sample data are ready."))
        self.stdout.write("Admin: admin@farmtime.test")
        self.stdout.write("Agriculturalist: agriculturalist@farmtime.test")
        self.stdout.write("Farmer: farmer@farmtime.test")
        self.stdout.write("All local demo accounts use the password documented in README. Never reuse it outside development.")

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

    def _notification(self, user, kind, title, body, target_url):
        Notification.objects.get_or_create(
            user=user,
            kind=kind,
            title=title,
            defaults={"body": body, "target_url": target_url},
        )
