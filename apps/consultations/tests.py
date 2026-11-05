from decimal import Decimal
from pathlib import Path
import shutil
from uuid import uuid4

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.farms.models import AreaUnit, Crop, Farm
from apps.notifications.models import Notification

from .models import Consultation, ConsultationMessage, ExpertRecommendation, FarmDataConsent


class ConsultationPermissionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        test_temp_root = Path(settings.BASE_DIR) / "tmp" / "test-media"
        test_temp_root.mkdir(parents=True, exist_ok=True)
        cls._media_directory = test_temp_root / f"consultations-{uuid4().hex}"
        cls._media_directory.mkdir()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_directory)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_directory, ignore_errors=True)

    def setUp(self):
        self.farmer = User.objects.create_user(
            email="owner@example.test", password="StrongPass123!", full_name="Farm Owner", role=User.Role.FARMER,
            is_verified=True,
        )
        self.other_farmer = User.objects.create_user(
            email="other@example.test", password="StrongPass123!", full_name="Other Farmer", role=User.Role.FARMER,
            is_verified=True,
        )
        self.expert = User.objects.create_user(
            email="expert@example.test", password="StrongPass123!", full_name="Approved Expert", role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        self.expert.agriculturalist_profile.is_approved = True
        self.expert.agriculturalist_profile.save(update_fields=["is_approved"])
        self.other_expert = User.objects.create_user(
            email="otherexpert@example.test", password="StrongPass123!", full_name="Other Expert", role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        self.other_expert.agriculturalist_profile.is_approved = True
        self.other_expert.agriculturalist_profile.save(update_fields=["is_approved"])
        self.farm = Farm.objects.create(
            owner=self.farmer,
            name="River Farm",
            district="Kurigram",
            land_area=Decimal("1.50"),
            area_unit=AreaUnit.ACRE,
        )

    def create_consultation(self):
        return Consultation.objects.create(
            farmer=self.farmer,
            agriculturalist=self.expert,
            farm=self.farm,
            title="Leaf discoloration",
            description="Rice leaves are turning yellow.",
            status=Consultation.Status.ASSIGNED,
        )

    def test_farmer_can_create_assigned_consultation_with_consent(self):
        self.client.force_login(self.farmer)
        response = self.client.post(
            reverse("farmer_consultations:create"),
            {
                "agriculturalist": self.expert.pk,
                "farm": self.farm.pk,
                "title": "Irrigation timing",
                "description": "When should I irrigate this week?",
                "priority": Consultation.Priority.NORMAL,
                "share_farm_data": "on",
                "consent_scope": FarmDataConsent.Scope.SUMMARY,
            },
        )
        self.assertEqual(response.status_code, 302)
        consultation = Consultation.objects.get(title="Irrigation timing")
        self.assertEqual(consultation.status, Consultation.Status.ASSIGNED)
        self.assertTrue(consultation.data_consent.is_active)
        self.assertTrue(Notification.objects.filter(user=self.expert, kind=Notification.Kind.CONSULTATION_ASSIGNED).exists())

    def test_farmer_cannot_read_another_farmers_consultation(self):
        consultation = self.create_consultation()
        self.client.force_login(self.other_farmer)
        response = self.client.get(reverse("farmer_consultations:detail", args=[consultation.pk]))
        self.assertEqual(response.status_code, 404)

    def test_unassigned_expert_cannot_read_case(self):
        consultation = self.create_consultation()
        self.client.force_login(self.other_expert)
        response = self.client.get(reverse("agriculturalist:question_detail", args=[consultation.pk]))
        self.assertEqual(response.status_code, 404)

    def test_assigned_expert_can_reply(self):
        consultation = self.create_consultation()
        self.client.force_login(self.expert)
        response = self.client.post(
            reverse("agriculturalist:reply", args=[consultation.pk]),
            {"body": "Please inspect soil moisture before the next irrigation."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ConsultationMessage.objects.filter(consultation=consultation, sender=self.expert).exists())
        consultation.refresh_from_db()
        self.assertEqual(consultation.status, Consultation.Status.ACTIVE)

    def test_assigned_expert_can_publish_recommendation_and_farmer_only_sees_published(self):
        consultation = self.create_consultation()
        self.client.force_login(self.expert)
        published_response = self.client.post(
            reverse("agriculturalist:recommend", args=[consultation.pk]),
            {
                "title": "Check soil moisture first",
                "explanation": "Inspect soil moisture before changing the irrigation schedule.",
                "priority": ExpertRecommendation.Priority.WATCH,
                "status": ExpertRecommendation.Status.PUBLISHED,
            },
        )
        draft_response = self.client.post(
            reverse("agriculturalist:recommend", args=[consultation.pk]),
            {
                "title": "Private draft recommendation",
                "explanation": "This draft still needs professional review.",
                "priority": ExpertRecommendation.Priority.INFO,
                "status": ExpertRecommendation.Status.DRAFT,
            },
        )
        self.assertEqual(published_response.status_code, 302)
        self.assertEqual(draft_response.status_code, 302)
        published = ExpertRecommendation.objects.get(title="Check soil moisture first")
        self.assertEqual(published.agriculturalist, self.expert)
        self.assertIsNotNone(published.published_at)
        self.assertTrue(
            Notification.objects.filter(
                user=self.farmer,
                kind=Notification.Kind.NEW_RECOMMENDATION,
                body=published.title,
            ).exists()
        )

        self.client.force_login(self.farmer)
        farmer_view = self.client.get(reverse("farmer_consultations:detail", args=[consultation.pk]))
        self.assertContains(farmer_view, published.title)
        self.assertNotContains(farmer_view, "Private draft recommendation")

    def test_unassigned_expert_cannot_submit_recommendation(self):
        consultation = self.create_consultation()
        self.client.force_login(self.other_expert)
        response = self.client.post(
            reverse("agriculturalist:recommend", args=[consultation.pk]),
            {
                "title": "Unauthorized recommendation",
                "explanation": "This expert is not assigned to the case.",
                "priority": ExpertRecommendation.Priority.INFO,
                "status": ExpertRecommendation.Status.PUBLISHED,
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ExpertRecommendation.objects.filter(title="Unauthorized recommendation").exists())

    def test_private_consultation_media_is_available_only_to_participants_and_admin(self):
        consultation = self.create_consultation()
        consultation.image = SimpleUploadedFile(
            "crop-question.jpg",
            b"private-question-image",
            content_type="image/jpeg",
        )
        consultation.save(update_fields=["image", "updated_at"])
        message = ConsultationMessage.objects.create(
            consultation=consultation,
            sender=self.farmer,
            body="Here is a closer image.",
            attachment=SimpleUploadedFile(
                "leaf-detail.png",
                b"private-message-attachment",
                content_type="image/png",
            ),
        )
        admin = User.objects.create_user(
            email="media-admin@example.test",
            password="StrongPass123!",
            full_name="Media Admin",
            role=User.Role.ADMIN,
            is_verified=True,
        )
        question_routes = [
            (self.farmer, reverse("farmer_consultations:question_image", args=[consultation.pk])),
            (self.expert, reverse("agriculturalist:question_image", args=[consultation.pk])),
            (admin, reverse("farmer_consultations:question_image", args=[consultation.pk])),
        ]
        attachment_routes = [
            (
                self.farmer,
                reverse("farmer_consultations:message_attachment", args=[consultation.pk, message.pk]),
            ),
            (
                self.expert,
                reverse("agriculturalist:message_attachment", args=[consultation.pk, message.pk]),
            ),
            (
                admin,
                reverse("farmer_consultations:message_attachment", args=[consultation.pk, message.pk]),
            ),
        ]
        for user, url in question_routes:
            self.client.force_login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"private-question-image")
            self.assertEqual(response["Cache-Control"], "private, no-store")
            self.assertIn("attachment", response["Content-Disposition"])
        for user, url in attachment_routes:
            self.client.force_login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"private-message-attachment")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")

        question_url = reverse("farmer_consultations:question_image", args=[consultation.pk])
        attachment_url = reverse(
            "farmer_consultations:message_attachment",
            args=[consultation.pk, message.pk],
        )
        for unrelated_user in (self.other_farmer, self.other_expert):
            self.client.force_login(unrelated_user)
            self.assertEqual(self.client.get(question_url).status_code, 404)
            self.assertEqual(self.client.get(attachment_url).status_code, 404)

        self.client.logout()
        self.assertEqual(self.client.get(question_url).status_code, 302)
        self.assertEqual(self.client.get(attachment_url).status_code, 302)

    def test_message_attachment_route_rejects_mismatched_consultation_id(self):
        consultation = self.create_consultation()
        other_consultation = Consultation.objects.create(
            farmer=self.farmer,
            agriculturalist=self.expert,
            title="Another case",
            description="A separate consultation.",
            status=Consultation.Status.ASSIGNED,
        )
        message = ConsultationMessage.objects.create(
            consultation=consultation,
            sender=self.farmer,
            body="Private attachment",
            attachment=SimpleUploadedFile("private.jpg", b"private", content_type="image/jpeg"),
        )
        self.client.force_login(self.farmer)
        response = self.client.get(
            reverse(
                "farmer_consultations:message_attachment",
                args=[other_consultation.pk, message.pk],
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_farm_analysis_only_shows_actively_consented_case(self):
        consultation = self.create_consultation()
        FarmDataConsent.objects.create(
            consultation=consultation,
            farmer=self.farmer,
            agriculturalist=self.expert,
            farm=self.farm,
            scope=FarmDataConsent.Scope.FULL,
        )
        self.client.force_login(self.expert)
        response = self.client.get(reverse("agriculturalist:analysis"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.farm.name)

    def test_case_simulator_runs_server_side_for_consented_case(self):
        consultation = self.create_consultation()
        FarmDataConsent.objects.create(
            consultation=consultation,
            farmer=self.farmer,
            agriculturalist=self.expert,
            farm=self.farm,
            scope=FarmDataConsent.Scope.SUMMARY,
        )
        crop = Crop.objects.create(name="Rice")
        self.client.force_login(self.expert)
        response = self.client.post(
            reverse("agriculturalist:simulator"),
            {
                "consultation": consultation.pk,
                "crop": crop.pk,
                "temperature_assumption": "34.0",
                "rainfall_assumption": "700.0",
                "irrigation_scenario": "MODERATE",
                "historical_year": "2025",
                "season": "AMAN",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rule-based illustration")

    def test_revoked_consent_is_removed_from_analysis_and_simulator(self):
        consultation = self.create_consultation()
        consent = FarmDataConsent.objects.create(
            consultation=consultation,
            farmer=self.farmer,
            agriculturalist=self.expert,
            farm=self.farm,
            scope=FarmDataConsent.Scope.FULL,
        )
        consent.revoke()
        crop = Crop.objects.create(name="Maize")
        self.client.force_login(self.expert)
        analysis = self.client.get(reverse("agriculturalist:analysis"))
        self.assertNotContains(analysis, self.farm.name)
        simulation = self.client.post(
            reverse("agriculturalist:simulator"),
            {
                "consultation": consultation.pk,
                "crop": crop.pk,
                "temperature_assumption": "30.0",
                "rainfall_assumption": "650.0",
                "irrigation_scenario": "MODERATE",
                "historical_year": "2025",
                "season": "AMAN",
            },
        )
        self.assertEqual(simulation.status_code, 200)
        self.assertNotContains(simulation, "Rule-based illustration")
        self.assertFormError(simulation.context["form"], "consultation", "Select a valid choice. That choice is not one of the available choices.")

    def test_farmer_can_regrant_consent_to_currently_assigned_expert(self):
        consultation = self.create_consultation()
        consent = FarmDataConsent.objects.create(
            consultation=consultation,
            farmer=self.farmer,
            agriculturalist=self.expert,
            farm=self.farm,
        )
        consent.revoke()
        consultation.agriculturalist = self.other_expert
        consultation.save(update_fields=["agriculturalist", "updated_at"])
        self.client.force_login(self.farmer)
        response = self.client.post(
            reverse("farmer_consultations:grant_consent", args=[consultation.pk]),
            {"scope": FarmDataConsent.Scope.FULL},
        )
        self.assertEqual(response.status_code, 302)
        consent.refresh_from_db()
        self.assertIsNone(consent.revoked_at)
        self.assertEqual(consent.agriculturalist, self.other_expert)
        self.assertEqual(consent.scope, FarmDataConsent.Scope.FULL)

    def test_history_and_weather_workspaces_render_for_approved_expert(self):
        self.client.force_login(self.expert)
        self.assertEqual(self.client.get(reverse("agriculturalist:history")).status_code, 200)
        self.assertEqual(self.client.get(reverse("agriculturalist:weather")).status_code, 200)


class PendingAgriculturalistTests(TestCase):
    def test_pending_agriculturalist_is_denied_expert_inbox(self):
        expert = User.objects.create_user(
            email="pending@example.test", password="StrongPass123!", full_name="Pending Expert", role=User.Role.AGRICULTURALIST
        )
        self.client.force_login(expert)
        response = self.client.get(reverse("agriculturalist:questions"))
        self.assertEqual(response.status_code, 403)
