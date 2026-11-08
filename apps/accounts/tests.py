import os
import re
import subprocess
import sys
from io import BytesIO
from unittest.mock import patch
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.administration.models import AuditLog

from .models import AgriculturalistProfile, AgriculturalistVerification, User
from .tokens import create_verification_token
from .validators import validate_profile_image
from .views import _client_address, _record_failed_login


class ImageUploadValidationTests(SimpleTestCase):
    def test_rejects_renamed_non_image_content(self):
        upload = SimpleUploadedFile("fake.png", b"<script>alert(1)</script>", content_type="image/png")
        with self.assertRaises(ValidationError):
            validate_profile_image(upload)

    def test_accepts_a_small_valid_png(self):
        payload = BytesIO()
        Image.new("RGB", (4, 4), "green").save(payload, format="PNG")
        upload = SimpleUploadedFile("avatar.png", payload.getvalue(), content_type="image/png")
        validate_profile_image(upload)


class AuthenticationWorkflowTests(TestCase):
    def setUp(self):
        cache.clear()

    def make_user(self, email, role, **extra):
        return User.objects.create_user(
            email=email,
            password="StrongLocalPass@2026",
            full_name=extra.pop("full_name", "Test User"),
            role=role,
            is_verified=extra.pop("is_verified", True),
            **extra,
        )

    @override_settings(EMAIL_VERIFICATION_ENABLED=False)
    def test_farmer_registration_creates_immediately_usable_account(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "account_type": User.Role.FARMER,
                "full_name": "New Farmer",
                "email": "NEW@Example.com",
                "phone_number": "01700000000",
                "district": "Rangpur",
                "upazila": "",
                "specialization": "",
                "qualifications": "",
                "password1": "StrongLocalPass@2026",
                "password2": "StrongLocalPass@2026",
                "agree_terms": "on",
            },
        )
        self.assertRedirects(response, reverse("accounts:login"))
        account = User.objects.get(email="new@example.com")
        self.assertEqual(account.role, User.Role.FARMER)
        self.assertFalse(account.is_staff)
        self.assertTrue(account.is_verified)
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(self.client.login(username=account.email, password="StrongLocalPass@2026"))
        self.assertRedirects(
            self.client.get(reverse("accounts:post_login")),
            reverse("dashboard:farmer_dashboard"),
        )

    @override_settings(EMAIL_VERIFICATION_ENABLED=True)
    def test_farmer_registration_keeps_verification_flow_ready_for_reenable(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "account_type": User.Role.FARMER,
                "full_name": "Future Verification Farmer",
                "email": "future-verification@example.com",
                "phone_number": "",
                "district": "Dhaka",
                "upazila": "",
                "specialization": "",
                "qualifications": "",
                "password1": "StrongLocalPass@2026",
                "password2": "StrongLocalPass@2026",
                "agree_terms": "on",
            },
        )
        self.assertRedirects(response, reverse("accounts:login"))
        account = User.objects.get(email="future-verification@example.com")
        self.assertFalse(account.is_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [account.email])

    def test_successful_email_login_creates_session_and_redirects_by_role(self):
        user = self.make_user("login@example.com", User.Role.FARMER)
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "LOGIN@EXAMPLE.COM", "password": "StrongLocalPass@2026"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:post_login"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertTrue(AuditLog.objects.filter(action="auth.login_succeeded", target_identifier=str(user.pk)).exists())
        role_redirect = self.client.get(response.url)
        self.assertRedirects(role_redirect, reverse("dashboard:farmer_dashboard"))

    @override_settings(EMAIL_VERIFICATION_ENABLED=False)
    def test_legacy_unverified_farmer_can_open_workspace_while_feature_is_disabled(self):
        user = self.make_user("pending-farmer@example.com", User.Role.FARMER, is_verified=False)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("dashboard:farmer_dashboard")).status_code, 200)
        self.assertRedirects(
            self.client.get(reverse("accounts:post_login")),
            reverse("dashboard:farmer_dashboard"),
        )

    @override_settings(EMAIL_VERIFICATION_ENABLED=True)
    def test_unverified_farmer_is_blocked_when_feature_is_reenabled(self):
        user = self.make_user("verification-required@example.com", User.Role.FARMER, is_verified=False)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("dashboard:farmer_dashboard")).status_code, 403)
        self.assertRedirects(
            self.client.get(reverse("accounts:post_login")),
            reverse("accounts:profile"),
        )

    def test_password_reset_email_token_flow_sets_new_password(self):
        user = self.make_user("reset@example.com", User.Role.FARMER)
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": user.email},
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [user.email])

        match = re.search(r"https?://[^\s]+(?P<path>/accounts/reset/[^\s]+/)", mail.outbox[0].body)
        self.assertIsNotNone(match, "The reset email must contain a reset URL.")
        token_response = self.client.get(urlparse(match.group(0)).path)
        self.assertEqual(token_response.status_code, 302)
        self.assertIn("/set-password/", token_response.url)

        form_page = self.client.get(token_response.url)
        self.assertEqual(form_page.status_code, 200)
        self.assertTrue(form_page.context["validlink"])
        new_password = "ChangedLocalPass@2026"
        completed = self.client.post(
            token_response.url,
            {"new_password1": new_password, "new_password2": new_password},
        )
        self.assertRedirects(completed, reverse("accounts:password_reset_complete"))
        self.assertTrue(self.client.login(username=user.email, password=new_password))

    @override_settings(EMAIL_VERIFICATION_ENABLED=True)
    def test_verification_token_marks_email_verified(self):
        user = self.make_user("verify@example.com", User.Role.FARMER, is_verified=False)
        response = self.client.get(reverse("accounts:verify_email", args=[create_verification_token(user)]))
        self.assertRedirects(response, reverse("accounts:login"))
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_each_role_redirects_to_its_own_dashboard(self):
        cases = [
            (User.Role.FARMER, "dashboard:farmer_dashboard"),
            (User.Role.AGRICULTURALIST, "dashboard:agriculturalist_dashboard"),
            (User.Role.ADMIN, "administration:dashboard"),
        ]
        for index, (role, destination) in enumerate(cases):
            user = self.make_user(f"role-{index}@example.com", role)
            self.client.force_login(user)
            self.assertRedirects(self.client.get(reverse("accounts:post_login")), reverse(destination))
            self.client.logout()

    def test_logout_is_post_only_and_clears_session(self):
        user = self.make_user("logout@example.com", User.Role.FARMER)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("core:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_form_cannot_change_role(self):
        user = self.make_user("farmer@example.com", User.Role.FARMER)
        self.client.force_login(user)
        self.client.post(
            reverse("accounts:profile"),
            {
                "full_name": "Farmer Updated",
                "email": user.email,
                "phone_number": "",
                "district": "Dhaka",
                "upazila": "",
                "role": User.Role.ADMIN,
                "experience": user.farmer_profile.experience,
                "preferred_area_unit": user.farmer_profile.preferred_area_unit,
                "bio": user.farmer_profile.bio,
            },
        )
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.FARMER)

    @override_settings(EMAIL_VERIFICATION_ENABLED=True)
    def test_changing_verified_email_starts_new_verification_cycle_when_enabled(self):
        user = self.make_user("verified@example.com", User.Role.FARMER, is_verified=True)
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "full_name": user.full_name,
                "email": "NEW-ADDRESS@Example.com",
                "phone_number": "",
                "district": "Dhaka",
                "upazila": "",
                "experience": user.farmer_profile.experience,
                "preferred_area_unit": user.farmer_profile.preferred_area_unit,
                "bio": user.farmer_profile.bio,
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.email, "new-address@example.com")
        self.assertFalse(user.is_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new-address@example.com"])
        self.assertTrue(AuditLog.objects.filter(action="account.email_changed", target_identifier=str(user.pk)).exists())

        match = re.search(r"https?://[^\s]+(?P<path>/accounts/verify/[^\s]+/)", mail.outbox[0].body)
        self.assertIsNotNone(match)
        self.client.get(urlparse(match.group(0)).path)
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    @override_settings(EMAIL_VERIFICATION_ENABLED=False)
    def test_changing_email_does_not_send_or_block_when_verification_is_disabled(self):
        user = self.make_user("legacy-unverified@example.com", User.Role.FARMER, is_verified=False)
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "full_name": user.full_name,
                "email": "UPDATED@Example.com",
                "phone_number": "",
                "district": "Dhaka",
                "upazila": "",
                "experience": user.farmer_profile.experience,
                "preferred_area_unit": user.farmer_profile.preferred_area_unit,
                "bio": user.farmer_profile.bio,
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.email, "updated@example.com")
        self.assertTrue(user.is_verified)
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(AuditLog.objects.filter(action="account.email_changed", target_identifier=str(user.pk)).exists())

    def test_profile_update_with_same_email_preserves_verification(self):
        user = self.make_user("same@example.com", User.Role.FARMER, is_verified=True)
        self.client.force_login(user)
        self.client.post(
            reverse("accounts:profile"),
            {
                "full_name": "Updated Name",
                "email": "SAME@EXAMPLE.COM",
                "phone_number": "",
                "district": "Rangpur",
                "upazila": "",
                "experience": user.farmer_profile.experience,
                "preferred_area_unit": user.farmer_profile.preferred_area_unit,
                "bio": user.farmer_profile.bio,
            },
        )
        user.refresh_from_db()
        self.assertTrue(user.is_verified)
        self.assertEqual(len(mail.outbox), 0)

    def test_unreviewed_agriculturalist_can_open_workspace(self):
        user = self.make_user("pending@example.com", User.Role.AGRICULTURALIST)
        self.assertFalse(AgriculturalistProfile.objects.get(user=user).is_approved)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("dashboard:agriculturalist_dashboard")).status_code, 200)

    @override_settings(EMAIL_VERIFICATION_ENABLED=False)
    def test_agriculturalist_signup_is_immediately_usable_with_review_status_disclosed(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "account_type": User.Role.AGRICULTURALIST,
                "full_name": "New Agriculturalist",
                "email": "new-expert@example.com",
                "phone_number": "",
                "district": "Dhaka",
                "upazila": "",
                "specialization": "Soil health",
                "qualifications": "BSc in Agriculture",
                "password1": "StrongLocalPass@2026",
                "password2": "StrongLocalPass@2026",
                "agree_terms": "on",
            },
        )

        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(email="new-expert@example.com")
        self.assertTrue(user.is_verified)
        self.assertFalse(user.agriculturalist_profile.is_approved)
        self.assertTrue(
            AgriculturalistVerification.objects.filter(
                agriculturalist=user.agriculturalist_profile,
                status=AgriculturalistVerification.Status.PENDING,
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 0)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("dashboard:agriculturalist_dashboard")).status_code, 200)
        self.assertRedirects(
            self.client.get(reverse("accounts:post_login")),
            reverse("dashboard:agriculturalist_dashboard"),
        )

    @override_settings(TRUST_X_FORWARDED_FOR=False)
    def test_login_throttle_ignores_untrusted_forwarded_for(self):
        request = RequestFactory().get(
            "/accounts/login/",
            REMOTE_ADDR="203.0.113.8",
            HTTP_X_FORWARDED_FOR="198.51.100.24",
        )
        self.assertEqual(_client_address(request), "203.0.113.8")

    @override_settings(TRUST_X_FORWARDED_FOR=True)
    def test_login_throttle_uses_forwarded_for_only_when_explicitly_trusted(self):
        request = RequestFactory().get(
            "/accounts/login/",
            REMOTE_ADDR="10.0.0.7",
            HTTP_X_FORWARDED_FOR="198.51.100.24, 10.0.0.6",
        )
        self.assertEqual(_client_address(request), "198.51.100.24")

    @patch("apps.accounts.views.cache")
    def test_failed_login_counter_uses_atomic_cache_operations(self, mocked_cache):
        mocked_cache.add.return_value = True
        _record_failed_login("login:203.0.113.8")
        mocked_cache.add.assert_called_once_with("login:203.0.113.8", 1, timeout=300)
        mocked_cache.incr.assert_not_called()
        mocked_cache.set.assert_not_called()

        mocked_cache.reset_mock()
        mocked_cache.add.return_value = False
        _record_failed_login("login:203.0.113.8")
        mocked_cache.incr.assert_called_once_with("login:203.0.113.8")
        mocked_cache.set.assert_not_called()

    def test_account_language_setting_uses_locale_middleware_cookie(self):
        user = self.make_user("language@example.com", User.Role.FARMER)
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:settings"),
            {"preferred_language": "bn"},
        )
        self.assertRedirects(response, reverse("accounts:settings"))
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "bn")
        user.refresh_from_db()
        self.assertEqual(user.preferred_language, "bn")
        public_page = self.client.get(reverse("core:home"))
        self.assertEqual(public_page.wsgi_request.LANGUAGE_CODE, "bn")
        self.assertContains(public_page, "অতীতকে বুঝুন।")

    def test_profile_image_uses_an_authenticated_self_only_endpoint(self):
        user = self.make_user("avatar@example.com", User.Role.FARMER)
        user.profile_image = "profiles/2026/11/avatar.png"
        user.save(update_fields=["profile_image"])

        anonymous = self.client.get(reverse("accounts:profile_image"))
        self.assertEqual(anonymous.status_code, 302)
        self.client.force_login(user)
        dashboard = self.client.get(reverse("dashboard:farmer_dashboard"))
        self.assertContains(dashboard, reverse("accounts:profile_image"))
        self.assertNotContains(dashboard, "/media/profiles/2026/11/avatar.png")
        missing_file = self.client.get(reverse("accounts:profile_image"))
        self.assertEqual(missing_file.status_code, 404)

    def test_farmer_can_complete_role_specific_profile_fields(self):
        user = self.make_user("profile-farmer@example.com", User.Role.FARMER)
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "full_name": "Profile Farmer",
                "email": user.email,
                "phone_number": "+880 1700-100001",
                "district": "Rangpur",
                "upazila": "Kaunia",
                "experience": "6_10",
                "preferred_area_unit": "BIGHA",
                "bio": "Grows rice and maize and wants collaborative crop-health guidance.",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        user.farmer_profile.refresh_from_db()
        self.assertEqual(user.phone_number, "+880 1700-100001")
        self.assertEqual(user.farmer_profile.experience, "6_10")
        self.assertEqual(user.farmer_profile.preferred_area_unit, "BIGHA")
        self.assertIn("crop-health", user.farmer_profile.bio)

    def test_agriculturalist_can_complete_professional_profile_fields(self):
        user = self.make_user("profile-agriculturalist@example.com", User.Role.AGRICULTURALIST)
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "full_name": "Profile Agriculturalist",
                "email": user.email,
                "phone_number": "+880 1700-100002",
                "district": "Kurigram",
                "upazila": "Ulipur",
                "specialization": "Rice disease and irrigation",
                "qualifications": "Demonstration agronomy profile",
                "organization": "Community Farm Lab",
                "license_number": "DEMO-PROFILE-01",
                "years_experience": "6",
                "bio": "Supports farmer-led diagnosis and evidence-aware decisions.",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        user.agriculturalist_profile.refresh_from_db()
        self.assertEqual(user.agriculturalist_profile.specialization, "Rice disease and irrigation")
        self.assertEqual(user.agriculturalist_profile.years_experience, 6)
        self.assertEqual(user.agriculturalist_profile.organization, "Community Farm Lab")
        self.assertFalse(user.agriculturalist_profile.is_approved)


class ProductionProxySettingsTests(SimpleTestCase):
    def _run_settings_assertion(self, flag, assertion):
        environment = os.environ.copy()
        environment.update(
            {
                "DJANGO_SECRET_KEY": "proxy-test-only-0123456789abcdefghijklmnopqrstuvwxyz-ABCDE",
                "ALLOWED_HOSTS": "example.com",
                "DATABASE_URL": "postgresql://check:check@127.0.0.1:5432/check",
                "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
                "CACHE_BACKEND": "django.core.cache.backends.redis.RedisCache",
                "CACHE_LOCATION": "redis://127.0.0.1:6379/15",
                "TRUST_X_FORWARDED_PROTO": flag,
            }
        )
        completed = subprocess.run(
            [sys.executable, "-c", assertion],
            cwd=settings.BASE_DIR,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_proxy_header_trust_is_explicitly_enabled(self):
        self._run_settings_assertion(
            "true",
            "from config.settings import production as p; "
            "assert p.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')",
        )

    def test_proxy_header_is_not_trusted_by_default(self):
        self._run_settings_assertion(
            "false",
            "from config.settings import production as p; "
            "assert getattr(p, 'SECURE_PROXY_SSL_HEADER', None) is None",
        )
