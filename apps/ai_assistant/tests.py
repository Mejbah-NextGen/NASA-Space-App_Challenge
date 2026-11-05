import json

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User

from .models import AIConversation, AIMessage


@override_settings(AI_API_KEY="", AI_API_BASE_URL="", AI_MODEL="", AI_RATE_LIMIT_PER_MINUTE=10)
class AssistantTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="assistant@example.test", password="StrongPass123!", full_name="Assistant User"
        )

    def test_chat_requires_login(self):
        response = self.client.post(
            reverse("ai_assistant:chat"), data=json.dumps({"message": "How should I irrigate?"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 302)

    def test_unconfigured_provider_returns_labeled_fallback_and_saves_history(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("ai_assistant:chat"),
            data=json.dumps({"message": "How should I improve irrigation?"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["fallback"])
        self.assertIn("Built-in", payload["source"])
        self.assertEqual(AIConversation.objects.filter(user=self.user).count(), 1)
        self.assertEqual(AIMessage.objects.count(), 2)

    @override_settings(AI_RATE_LIMIT_PER_MINUTE=1)
    def test_chat_is_rate_limited(self):
        self.client.force_login(self.user)
        endpoint = reverse("ai_assistant:chat")
        body = json.dumps({"message": "Tell me about soil."})
        self.assertEqual(self.client.post(endpoint, data=body, content_type="application/json").status_code, 200)
        self.assertEqual(self.client.post(endpoint, data=body, content_type="application/json").status_code, 429)
