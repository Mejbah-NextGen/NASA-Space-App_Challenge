from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

from .models import LearningArticle, LearningCategory


class LearningArticleTests(TestCase):
    def setUp(self):
        self.expert = User.objects.create_user(
            email="writer@example.test",
            password="StrongPass123!",
            full_name="Expert Writer",
            role=User.Role.AGRICULTURALIST,
            is_verified=True,
        )
        self.expert.agriculturalist_profile.is_approved = True
        self.expert.agriculturalist_profile.save(update_fields=["is_approved"])
        self.category = LearningCategory.objects.create(name="Irrigation", slug="irrigation")
        self.published = LearningArticle.objects.create(
            category=self.category,
            author=self.expert,
            title="Water at the right time",
            summary="A reviewed irrigation guide.",
            body="Check soil moisture before irrigating.",
            status=LearningArticle.Status.PUBLISHED,
        )
        self.draft = LearningArticle.objects.create(
            category=self.category,
            author=self.expert,
            title="Unreviewed draft",
            summary="Not public.",
            body="Draft guidance.",
        )

    def test_public_list_shows_only_published_articles(self):
        response = self.client.get(reverse("learning:list"))
        self.assertContains(response, self.published.title)
        self.assertNotContains(response, self.draft.title)

    def test_anonymous_user_cannot_read_draft(self):
        response = self.client.get(reverse("learning:detail", args=[self.draft.slug]))
        self.assertEqual(response.status_code, 404)

    def test_approved_author_can_submit_own_draft(self):
        self.client.force_login(self.expert)
        response = self.client.post(reverse("learning:submit", args=[self.draft.pk]))
        self.assertEqual(response.status_code, 302)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, LearningArticle.Status.SUBMITTED)
