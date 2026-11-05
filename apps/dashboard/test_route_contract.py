from django.test import TestCase

from apps.accounts.models import User


class RequiredRouteContractTests(TestCase):
    def assert_routes(self, routes, allowed_statuses=(200,)):
        for route in routes:
            with self.subTest(route=route):
                self.assertIn(self.client.get(route).status_code, allowed_statuses)

    def test_public_and_auth_routes_exist(self):
        self.assert_routes(
            [
                "/",
                "/weather/",
                "/history/",
                "/crop-insights/",
                "/about/",
                "/how-it-works/",
                "/data-sources/",
                "/accounts/login/",
                "/accounts/signup/",
                "/accounts/forgot-password/",
            ]
        )
        self.assertEqual(self.client.get("/accounts/logout/").status_code, 302)

    def test_farmer_routes_exist_and_render_for_verified_farmer(self):
        farmer = User.objects.create_user(
            email="route-farmer@example.com",
            password="StrongLocalPass@2026",
            full_name="Route Farmer",
            role=User.Role.FARMER,
            is_verified=True,
        )
        self.client.force_login(farmer)
        self.assert_routes(
            [
                "/accounts/profile/",
                "/accounts/settings/",
                "/farmer/dashboard/",
                "/farmer/farms/",
                "/farmer/history/",
                "/farmer/simulator/",
                "/farmer/decisions/",
                "/farmer/consultations/",
                "/farmer/weather/",
                "/farmer/learning/",
                "/farmer/support/",
                "/farmer/data-sources/",
            ],
            allowed_statuses=(200, 302),
        )

    def test_agriculturalist_routes_exist_and_render_for_approved_expert(self):
        expert = User.objects.create_user(
            email="route-expert@example.com",
            password="StrongLocalPass@2026",
            full_name="Route Expert",
            role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        expert.agriculturalist_profile.is_approved = True
        expert.agriculturalist_profile.save(update_fields=["is_approved"])
        self.client.force_login(expert)
        self.assert_routes(
            [
                "/agriculturalist/dashboard/",
                "/agriculturalist/farmers/",
                "/agriculturalist/analysis/",
                "/agriculturalist/history/",
                "/agriculturalist/simulator/",
                "/agriculturalist/recommendations/",
                "/agriculturalist/questions/",
                "/agriculturalist/weather/",
                "/agriculturalist/learning/",
            ],
            allowed_statuses=(200, 302),
        )

    def test_custom_admin_routes_exist_and_render_for_platform_admin(self):
        admin_user = User.objects.create_user(
            email="route-admin@example.com",
            password="StrongLocalPass@2026",
            full_name="Route Admin",
            role=User.Role.ADMIN,
            is_verified=True,
            is_staff=True,
        )
        self.client.force_login(admin_user)
        self.assert_routes(
            [
                "/platform-admin/dashboard/",
                "/platform-admin/users/",
                "/platform-admin/agriculturalists/",
                "/platform-admin/farmers/",
                "/platform-admin/data/",
                "/platform-admin/farms/",
                "/platform-admin/assignments/",
                "/platform-admin/reports/",
                "/platform-admin/weather/",
                "/platform-admin/content/",
                "/platform-admin/settings/",
                "/platform-admin/logs/",
            ]
        )
