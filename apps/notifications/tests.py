from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

from .models import Notification


class NotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="notify@example.test", password="StrongPass123!", full_name="Notify User"
        )
        self.other = User.objects.create_user(
            email="othernotify@example.test", password="StrongPass123!", full_name="Other User"
        )
        self.notification = Notification.objects.create(user=self.user, title="Update", body="A new update")

    def test_mark_read_requires_owner_and_post(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse("notifications:mark_read", args=[self.notification.pk])).status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("notifications:mark_read", args=[self.notification.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse("notifications:mark_read", args=[self.notification.pk])).status_code, 302)
        self.notification.refresh_from_db()
        self.assertIsNotNone(self.notification.read_at)

    def test_mark_all_read_is_scoped_to_current_user(self):
        other_notification = Notification.objects.create(user=self.other, title="Private")
        self.client.force_login(self.user)
        self.client.post(reverse("notifications:mark_all_read"))
        self.notification.refresh_from_db()
        other_notification.refresh_from_db()
        self.assertIsNotNone(self.notification.read_at)
        self.assertIsNone(other_notification.read_at)
