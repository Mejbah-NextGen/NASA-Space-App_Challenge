from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class DashboardIntegrationTests(TestCase):
    def test_farmer_dashboard_renders_shared_navigation(self):
        farmer = User.objects.create_user(
            email="farmer-dashboard@example.com",
            password="StrongLocalPass@2026",
            full_name="Farmer Dashboard",
            role=User.Role.FARMER,
            is_verified=True,
        )
        self.client.force_login(farmer)
        response = self.client.get(reverse("dashboard:farmer_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Assistant")
        self.assertContains(response, "feature-grid")
        self.assertContains(response, "My Farm")
        self.assertNotContains(response, '<a href="/assistant/">AI Farm Assistant</a>')

    def test_approved_agriculturalist_dashboard_renders(self):
        expert = User.objects.create_user(
            email="expert-dashboard@example.com",
            password="StrongLocalPass@2026",
            full_name="Expert Dashboard",
            role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        expert.agriculturalist_profile.is_approved = True
        expert.agriculturalist_profile.save(update_fields=["is_approved"])
        self.client.force_login(expert)
        response = self.client.get(reverse("dashboard:agriculturalist_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assigned Farmers")

    def test_cross_role_dashboard_access_is_denied(self):
        farmer = User.objects.create_user(
            email="private-dashboard@example.com",
            password="StrongLocalPass@2026",
            full_name="Private Farmer",
            role=User.Role.FARMER,
            is_verified=True,
        )
        self.client.force_login(farmer)
        self.assertEqual(self.client.get(reverse("administration:dashboard")).status_code, 403)

    def test_responsive_feature_grid_contract_matches_mobile_tablet_and_desktop_navigation(self):
        css = (settings.BASE_DIR / "static" / "css" / "app.css").read_text(encoding="utf-8")
        self.assertIn(".feature-grid { display: grid; grid-template-columns: repeat(2", css)
        self.assertIn("@media (min-width: 768px)", css)
        self.assertIn(".feature-grid { grid-template-columns: repeat(3", css)
        self.assertIn("@media (min-width: 1200px)", css)
        self.assertIn(".workspace-sidebar.open { transform: translateX(0); }", css)
        self.assertIn(".workspace-sidebar { transform: none; }", css)
