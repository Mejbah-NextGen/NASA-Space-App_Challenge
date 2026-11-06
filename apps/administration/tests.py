from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AgriculturalistVerification, User
from apps.agricultural_data.models import AgriculturalDataset, DataImportJob, DataSource, Region
from apps.consultations.models import Consultation, ExpertAssignment, FarmDataConsent
from apps.consultations.services import assign_consultation
from apps.core.models import PlatformSetting, SupportTicket
from apps.farms.models import AreaUnit, Crop, Farm
from apps.notifications.models import Notification
from apps.weather.models import WeatherAlert

from .forms import ExpertAssignmentForm
from .models import AuditLog


class AdministrationWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="platform-admin@example.com",
            password="StrongLocalPass@2026",
            full_name="Platform Admin",
            role=User.Role.ADMIN,
            is_verified=True,
            is_staff=True,
        )
        self.client.force_login(self.admin)

    def test_admin_can_suspend_another_user_with_audit_record(self):
        farmer = User.objects.create_user(
            email="managed-farmer@example.com",
            password="StrongLocalPass@2026",
            full_name="Managed Farmer",
            role=User.Role.FARMER,
        )
        response = self.client.post(reverse("administration:user_status", args=[farmer.pk]), {"action": "suspend"})
        self.assertRedirects(response, reverse("administration:users"))
        farmer.refresh_from_db()
        self.assertFalse(farmer.is_active)
        self.assertTrue(AuditLog.objects.filter(action="user.suspend", target_identifier=str(farmer.pk)).exists())

    def test_admin_can_view_read_only_user_details(self):
        farmer = User.objects.create_user(
            email="detail-farmer@example.com",
            password="StrongLocalPass@2026",
            full_name="Detail Farmer",
            role=User.Role.FARMER,
        )
        Farm.objects.create(
            owner=farmer,
            name="Detail Farm",
            district="Kurigram",
            land_area=Decimal("1.00"),
            area_unit=AreaUnit.ACRE,
        )

        response = self.client.get(reverse("administration:user_detail", args=[farmer.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, farmer.email)
        self.assertEqual(response.context["farm_count"], 1)

    def test_admin_approval_enables_expert_access(self):
        expert = User.objects.create_user(
            email="applicant@example.com",
            password="StrongLocalPass@2026",
            full_name="Expert Applicant",
            role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        verification = AgriculturalistVerification.objects.create(agriculturalist=expert.agriculturalist_profile)
        response = self.client.post(
            reverse("administration:agriculturalist_review", args=[verification.pk]),
            {"status": AgriculturalistVerification.Status.APPROVED, "notes": "Credentials reviewed."},
        )
        self.assertRedirects(response, reverse("administration:agriculturalists"))
        expert.refresh_from_db()
        expert.agriculturalist_profile.refresh_from_db()
        self.assertTrue(expert.is_verified)
        self.assertTrue(expert.agriculturalist_profile.is_approved)

    def test_admin_can_reject_expert_application(self):
        expert = User.objects.create_user(
            email="rejected-applicant@example.com",
            password="StrongLocalPass@2026",
            full_name="Rejected Applicant",
            role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        verification = AgriculturalistVerification.objects.create(agriculturalist=expert.agriculturalist_profile)

        response = self.client.post(
            reverse("administration:agriculturalist_review", args=[verification.pk]),
            {"status": AgriculturalistVerification.Status.REJECTED, "notes": "Credentials could not be verified."},
        )

        self.assertRedirects(response, reverse("administration:agriculturalists"))
        expert.refresh_from_db()
        expert.agriculturalist_profile.refresh_from_db()
        self.assertTrue(expert.is_verified)
        self.assertFalse(expert.agriculturalist_profile.is_approved)
        self.assertTrue(AuditLog.objects.filter(action="expert.rejected", target_identifier=str(expert.pk)).exists())

    @override_settings(EMAIL_VERIFICATION_ENABLED=True)
    def test_professional_approval_does_not_bypass_email_verification_when_enabled(self):
        expert = User.objects.create_user(
            email="unverified-applicant@example.com",
            password="StrongLocalPass@2026",
            full_name="Unverified Applicant",
            role=User.Role.AGRICULTURALIST,
            is_verified=False,
        )
        verification = AgriculturalistVerification.objects.create(agriculturalist=expert.agriculturalist_profile)
        self.client.post(
            reverse("administration:agriculturalist_review", args=[verification.pk]),
            {"status": AgriculturalistVerification.Status.APPROVED, "notes": "Professional credentials approved."},
        )
        expert.refresh_from_db()
        expert.agriculturalist_profile.refresh_from_db()
        self.assertTrue(expert.agriculturalist_profile.is_approved)
        self.assertFalse(expert.is_verified)
        self.client.force_login(expert)
        self.assertEqual(self.client.get(reverse("dashboard:agriculturalist_dashboard")).status_code, 403)

    @override_settings(EMAIL_VERIFICATION_ENABLED=False)
    def test_approved_expert_is_not_blocked_by_email_verification_when_disabled(self):
        expert = User.objects.create_user(
            email="temporarily-unverified-applicant@example.com",
            password="StrongLocalPass@2026",
            full_name="Approved Applicant",
            role=User.Role.AGRICULTURALIST,
            is_verified=False,
        )
        verification = AgriculturalistVerification.objects.create(agriculturalist=expert.agriculturalist_profile)
        self.client.post(
            reverse("administration:agriculturalist_review", args=[verification.pk]),
            {"status": AgriculturalistVerification.Status.APPROVED, "notes": "Credentials approved."},
        )
        expert.agriculturalist_profile.refresh_from_db()
        self.assertTrue(expert.agriculturalist_profile.is_approved)
        self.client.force_login(expert)
        self.assertEqual(self.client.get(reverse("dashboard:agriculturalist_dashboard")).status_code, 200)

    def test_csv_export_escapes_formula_prefixes(self):
        User.objects.create_user(
            email="formula@example.com",
            password="StrongLocalPass@2026",
            full_name="=DANGEROUS()",
            role=User.Role.FARMER,
        )
        response = self.client.get(reverse("administration:report_export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("'=DANGEROUS()", response.content.decode())

    def test_admin_can_assign_approved_expert_to_pending_consultation(self):
        farmer = User.objects.create_user(
            email="assignment-farmer@example.com",
            password="StrongLocalPass@2026",
            full_name="Assignment Farmer",
            role=User.Role.FARMER,
        )
        expert = User.objects.create_user(
            email="assignment-expert@example.com",
            password="StrongLocalPass@2026",
            full_name="Assignment Expert",
            role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        expert.agriculturalist_profile.is_approved = True
        expert.agriculturalist_profile.save(update_fields=["is_approved"])
        consultation = Consultation.objects.create(
            farmer=farmer,
            title="Pending assignment",
            description="Please assign a verified expert.",
        )
        response = self.client.post(
            reverse("administration:assignment_action"),
            {"consultation": consultation.pk, "agriculturalist": expert.pk},
        )
        self.assertRedirects(response, reverse("administration:assignments"))
        consultation.refresh_from_db()
        self.assertEqual(consultation.agriculturalist, expert)
        self.assertEqual(consultation.status, Consultation.Status.ASSIGNED)
        self.assertTrue(ExpertAssignment.objects.filter(consultation=consultation, agriculturalist=expert).exists())

    def test_assignment_form_applies_email_verification_filter_only_when_enabled(self):
        expert = User.objects.create_user(
            email="filter-expert@example.com",
            password="StrongLocalPass@2026",
            full_name="Filter Expert",
            role=User.Role.AGRICULTURALIST,
            is_verified=False,
        )
        expert.agriculturalist_profile.is_approved = True
        expert.agriculturalist_profile.save(update_fields=["is_approved"])

        for enabled, should_be_available in ((False, True), (True, False)):
            with self.subTest(email_verification_enabled=enabled), self.settings(
                EMAIL_VERIFICATION_ENABLED=enabled
            ):
                form = ExpertAssignmentForm()
                is_available = form.fields["agriculturalist"].queryset.filter(pk=expert.pk).exists()
                self.assertEqual(is_available, should_be_available)

    def test_admin_reassignment_revokes_old_consent_and_records_previous_expert(self):
        farmer = User.objects.create_user(
            email="reassignment-farmer@example.com",
            password="StrongLocalPass@2026",
            full_name="Reassignment Farmer",
            role=User.Role.FARMER,
        )
        old_expert = User.objects.create_user(
            email="old-expert@example.com",
            password="StrongLocalPass@2026",
            full_name="Old Expert",
            role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        new_expert = User.objects.create_user(
            email="new-expert@example.com",
            password="StrongLocalPass@2026",
            full_name="New Expert",
            role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        for expert in (old_expert, new_expert):
            expert.agriculturalist_profile.is_approved = True
            expert.agriculturalist_profile.save(update_fields=["is_approved"])
        farm = Farm.objects.create(
            owner=farmer,
            name="Consent Farm",
            district="Kurigram",
            land_area=Decimal("1.25"),
            area_unit=AreaUnit.ACRE,
        )
        consultation = Consultation.objects.create(
            farmer=farmer,
            agriculturalist=old_expert,
            farm=farm,
            title="Reassign this case",
            description="The original expert is unavailable.",
            status=Consultation.Status.ACTIVE,
        )
        assign_consultation(consultation, assigned_by=self.admin, share_farm=True)
        response = self.client.post(
            reverse("administration:assignment_action"),
            {"consultation": consultation.pk, "agriculturalist": new_expert.pk},
        )
        self.assertRedirects(response, reverse("administration:assignments"))
        consultation.refresh_from_db()
        consent = FarmDataConsent.objects.get(consultation=consultation)
        assignment = ExpertAssignment.objects.get(consultation=consultation)
        self.assertEqual(consultation.agriculturalist, new_expert)
        self.assertEqual(assignment.agriculturalist, new_expert)
        self.assertIsNotNone(consent.revoked_at)
        audit = AuditLog.objects.get(action="consultation.expert_assigned", target_identifier=str(consultation.pk))
        self.assertEqual(audit.metadata["previous_agriculturalist_id"], old_expert.pk)
        self.assertTrue(
            Notification.objects.filter(
                user=old_expert,
                kind=Notification.Kind.CONSULTATION_UPDATED,
                title="Consultation reassigned",
            ).exists()
        )

    def test_reassigning_same_expert_is_a_no_op(self):
        farmer = User.objects.create_user(
            email="same-farmer@example.com",
            password="StrongLocalPass@2026",
            full_name="Same Farmer",
            role=User.Role.FARMER,
        )
        expert = User.objects.create_user(
            email="same-expert@example.com",
            password="StrongLocalPass@2026",
            full_name="Same Expert",
            role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        expert.agriculturalist_profile.is_approved = True
        expert.agriculturalist_profile.save(update_fields=["is_approved"])
        consultation = Consultation.objects.create(
            farmer=farmer,
            agriculturalist=expert,
            title="Keep this active",
            description="No actual reassignment needed.",
            status=Consultation.Status.ACTIVE,
        )
        assign_consultation(consultation, assigned_by=self.admin)
        response = self.client.post(
            reverse("administration:assignment_action"),
            {"consultation": consultation.pk, "agriculturalist": expert.pk},
        )
        self.assertRedirects(response, reverse("administration:assignments"))
        consultation.refresh_from_db()
        self.assertEqual(consultation.status, Consultation.Status.ACTIVE)

    def weather_dependencies(self):
        region = Region.objects.create(district="Kurigram", upazila="Sadar")
        source = DataSource.objects.create(
            name="Test weather provider",
            provider="Test provider",
            kind=DataSource.Kind.WEATHER,
            is_active=True,
        )
        return region, source

    def test_admin_can_create_and_deactivate_weather_alert_with_audit(self):
        region, source = self.weather_dependencies()
        starts_at = timezone.now() + timedelta(hours=1)
        ends_at = starts_at + timedelta(days=1)
        response = self.client.post(
            reverse("administration:weather_alert_create"),
            {
                "region": region.pk,
                "source": source.pk,
                "title": "Heavy rain watch",
                "description": "Heavy rainfall may affect low fields.",
                "recommendation": "Inspect drainage and follow official guidance.",
                "severity": WeatherAlert.Severity.WATCH,
                "starts_at": starts_at.strftime("%Y-%m-%d %H:%M:%S"),
                "ends_at": ends_at.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        self.assertRedirects(response, reverse("administration:weather"))
        alert = WeatherAlert.objects.get(title="Heavy rain watch")
        self.assertTrue(alert.is_active)
        self.assertTrue(
            AuditLog.objects.filter(action="weather_alert.created", target_identifier=str(alert.pk)).exists()
        )

        response = self.client.post(
            reverse("administration:weather_alert_toggle", args=[alert.pk]),
            {"action": "deactivate"},
        )
        self.assertRedirects(response, reverse("administration:weather"))
        alert.refresh_from_db()
        self.assertFalse(alert.is_active)
        self.assertTrue(
            AuditLog.objects.filter(action="weather_alert.deactivated", target_identifier=str(alert.pk)).exists()
        )

    def test_invalid_weather_window_is_rejected(self):
        region, source = self.weather_dependencies()
        starts_at = timezone.now() + timedelta(days=1)
        response = self.client.post(
            reverse("administration:weather_alert_create"),
            {
                "region": region.pk,
                "source": source.pk,
                "title": "Invalid window",
                "description": "This should not be saved.",
                "recommendation": "None",
                "severity": WeatherAlert.Severity.INFO,
                "starts_at": starts_at.strftime("%Y-%m-%d %H:%M:%S"),
                "ends_at": (starts_at - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "must be after its start time", status_code=400)
        self.assertFalse(WeatherAlert.objects.exists())

    def test_non_admin_cannot_create_weather_alert(self):
        region, source = self.weather_dependencies()
        farmer = User.objects.create_user(
            email="unauthorized-weather@example.com",
            password="StrongLocalPass@2026",
            full_name="Unauthorized Farmer",
            role=User.Role.FARMER,
        )
        self.client.force_login(farmer)
        response = self.client.post(
            reverse("administration:weather_alert_create"),
            {"region": region.pk, "source": source.pk, "title": "Unauthorized"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(WeatherAlert.objects.exists())

    def test_support_ticket_update_is_audited_and_notifies_account_holder(self):
        farmer = User.objects.create_user(
            email="ticket-owner@example.com",
            password="StrongLocalPass@2026",
            full_name="Ticket Owner",
            role=User.Role.FARMER,
        )
        ticket = SupportTicket.objects.create(
            user=farmer,
            name=farmer.full_name,
            email=farmer.email,
            subject="Weather card problem",
            message="The local weather card has not refreshed since yesterday.",
        )
        detail = self.client.get(reverse("administration:support_ticket", args=[ticket.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Weather card problem")
        response = self.client.post(
            reverse("administration:support_ticket", args=[ticket.pk]),
            {
                "status": SupportTicket.Status.RESOLVED,
                "priority": SupportTicket.Priority.HIGH,
                "staff_response": "We refreshed the provider cache and confirmed the update.",
            },
        )
        self.assertRedirects(response, reverse("administration:support_ticket", args=[ticket.pk]))
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, SupportTicket.Status.RESOLVED)
        self.assertEqual(ticket.priority, SupportTicket.Priority.HIGH)
        audit = AuditLog.objects.get(action="support_ticket.updated", target_identifier=str(ticket.pk))
        self.assertTrue(audit.metadata["response_updated"])
        self.assertNotIn("provider cache", str(audit.metadata))
        self.assertTrue(
            Notification.objects.filter(
                user=farmer,
                kind=Notification.Kind.SUPPORT_UPDATED,
                title="Support ticket updated",
            ).exists()
        )

    def test_only_public_platform_settings_are_editable(self):
        public = PlatformSetting.objects.create(
            key="homepage-banner",
            value={"enabled": False},
            description="Public homepage banner.",
            is_public=True,
        )
        private = PlatformSetting.objects.create(
            key="internal-integration",
            value={"credential_reference": "never-show"},
            description="Private deployment setting.",
            is_public=False,
        )
        settings_page = self.client.get(reverse("administration:settings"))
        self.assertContains(settings_page, "homepage-banner")
        self.assertNotContains(settings_page, "internal-integration")
        self.assertNotContains(settings_page, "never-show")
        response = self.client.post(
            reverse("administration:public_setting_update", args=[public.pk]),
            {"description": "Public seasonal banner.", "value": '{"enabled": true, "message": "Harvest"}'},
        )
        self.assertRedirects(response, reverse("administration:settings"))
        public.refresh_from_db()
        self.assertEqual(public.value["message"], "Harvest")
        self.assertTrue(
            AuditLog.objects.filter(action="platform_setting.updated", target_identifier=str(public.pk)).exists()
        )
        denied = self.client.post(
            reverse("administration:public_setting_update", args=[private.pk]),
            {"description": "Changed", "value": '{"credential_reference": "exposed"}'},
        )
        self.assertEqual(denied.status_code, 404)
        private.refresh_from_db()
        self.assertEqual(private.value["credential_reference"], "never-show")

    def test_admin_can_manage_source_dataset_and_crop_catalog_with_audits(self):
        source_response = self.client.post(
            reverse("administration:data_source_create"),
            {
                "name": "Reviewed crop bureau",
                "provider": "Test provider",
                "kind": DataSource.Kind.CROP,
                "url": "https://example.test/source",
                "description": "Reviewed test source.",
                "attribution": "Test attribution",
                "geographic_coverage": "Kurigram",
                "update_frequency": "Annual",
                "limitations": "Test-only records.",
                "is_active": "on",
                "last_updated_at": "",
            },
        )
        self.assertRedirects(source_response, reverse("administration:data"))
        source = DataSource.objects.get(name="Reviewed crop bureau")
        self.assertTrue(AuditLog.objects.filter(action="data_source.created", target_identifier=str(source.pk)).exists())

        dataset_response = self.client.post(
            reverse("administration:dataset_create"),
            {
                "source": source.pk,
                "title": "Reviewed crop dataset",
                "slug": "reviewed-crop-dataset",
                "description": "Validated annual production observations.",
                "status": AgriculturalDataset.Status.VERIFIED,
                "geographic_coverage": "Kurigram",
                "date_start": "2020-01-01",
                "date_end": "2025-12-31",
                "units": "tonnes and tonnes/hectare",
                "quality_notes": "Reviewed for test coverage.",
                "metadata": '{"license": "test"}',
            },
        )
        self.assertRedirects(dataset_response, reverse("administration:data"))
        dataset = AgriculturalDataset.objects.get(slug="reviewed-crop-dataset")
        self.assertTrue(
            AuditLog.objects.filter(action="agricultural_dataset.created", target_identifier=str(dataset.pk)).exists()
        )

        crop_response = self.client.post(
            reverse("administration:crop_create"),
            {"name": "Lentil", "variety": "BARI Masur", "is_supported": "on"},
        )
        self.assertRedirects(crop_response, reverse("administration:data"))
        crop = Crop.objects.get(name="Lentil", variety="BARI Masur")
        toggle = self.client.post(
            reverse("administration:crop_toggle", args=[crop.pk]),
            {"action": "disable"},
        )
        self.assertRedirects(toggle, reverse("administration:data"))
        crop.refresh_from_db()
        self.assertFalse(crop.is_supported)
        self.assertTrue(
            AuditLog.objects.filter(action="crop_catalog.deactivated", target_identifier=str(crop.pk)).exists()
        )

    def test_demo_source_cannot_back_a_verified_dataset(self):
        source = DataSource.objects.create(
            name="Demo-only source",
            provider="Local demonstration",
            kind=DataSource.Kind.CROP,
            is_demo=True,
        )
        response = self.client.post(
            reverse("administration:dataset_create"),
            {
                "source": source.pk,
                "title": "Invalid verified sample",
                "slug": "invalid-verified-sample",
                "description": "This must not be accepted.",
                "status": AgriculturalDataset.Status.VERIFIED,
                "geographic_coverage": "Kurigram",
                "date_start": "2020-01-01",
                "date_end": "2025-12-31",
                "units": "tonnes",
                "quality_notes": "Sample only.",
                "metadata": "{}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "demonstration source cannot be marked verified")
        self.assertFalse(AgriculturalDataset.objects.filter(slug="invalid-verified-sample").exists())

    def test_admin_csv_import_failure_is_recorded_and_visible(self):
        source = DataSource.objects.create(
            name="Import test source",
            provider="Local test provider",
            kind=DataSource.Kind.HISTORICAL_WEATHER,
            is_demo=True,
        )
        dataset = AgriculturalDataset.objects.create(
            source=source,
            title="Import test dataset",
            slug="import-test-dataset",
            status=AgriculturalDataset.Status.SAMPLE,
        )
        upload = SimpleUploadedFile(
            "broken.csv",
            b"district,rainfall_mm\nKurigram,12\n",
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("administration:data"),
            {"dataset": dataset.pk, "kind": DataImportJob.Kind.WEATHER, "csv_file": upload},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        job = DataImportJob.objects.get(dataset=dataset)
        self.assertEqual(job.status, DataImportJob.Status.FAILED)
        self.assertTrue(job.errors)
        self.assertContains(response, "Import failed")
