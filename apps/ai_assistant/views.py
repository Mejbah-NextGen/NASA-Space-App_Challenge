import json

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .models import AIConversation, AIMessage
from .services import generate_reply, provider_is_configured


SUGGESTED_QUESTIONS = [
    "What crop should I consider this season?",
    "How can I improve irrigation?",
    "What does historical rainfall show?",
    "How can I protect crops during heavy rain?",
    "What are common soil management practices?",
]


def _allow_request(user_id):
    minute = timezone.now().strftime("%Y%m%d%H%M")
    key = f"ai-rate:{user_id}:{minute}"
    limit = max(1, int(settings.AI_RATE_LIMIT_PER_MINUTE))
    if cache.add(key, 1, timeout=70):
        return True
    try:
        count = cache.incr(key)
    except ValueError:
        # A backend may evict the key between add() and incr(); recreate it.
        cache.set(key, 1, timeout=70)
        count = 1
    return count <= limit


class AssistantPanelView(LoginRequiredMixin, TemplateView):
    template_name = "ai_assistant/panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversations = AIConversation.objects.filter(user=self.request.user).prefetch_related("messages")
        requested = self.request.GET.get("conversation")
        selected = conversations.filter(pk=requested).first() if requested else conversations.first()
        context.update(
            {
                "conversations": conversations,
                "conversation": selected,
                "suggested_questions": SUGGESTED_QUESTIONS,
                "provider_configured": provider_is_configured(),
            }
        )
        return context


class ChatView(LoginRequiredMixin, View):
    def post(self, request):
        if not _allow_request(request.user.pk):
            return JsonResponse({"error": "Too many messages. Please wait a minute and try again."}, status=429)
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON request."}, status=400)
        content = str(payload.get("message", "")).strip()
        if not content:
            return JsonResponse({"error": "Write a question before sending."}, status=400)
        conversation_id = payload.get("conversation_id")
        if conversation_id:
            conversation = get_object_or_404(AIConversation, pk=conversation_id, user=request.user)
        else:
            session_conversation_id = request.session.get("ai_conversation_id")
            conversation = AIConversation.objects.filter(pk=session_conversation_id, user=request.user).first()
            if conversation is None:
                conversation = AIConversation.objects.create(user=request.user, title=content[:80])
        request.session["ai_conversation_id"] = conversation.pk
        recent = list(conversation.messages.order_by("-created_at")[:8])[::-1]
        try:
            result = generate_reply(user=request.user, message=content, recent_messages=recent)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        user_message = AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content=content)
        assistant_message = AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.Role.ASSISTANT,
            content=result.content,
            source_label=result.source_label,
            is_fallback=result.is_fallback,
        )
        conversation.save(update_fields=["updated_at"])
        return JsonResponse(
            {
                "conversation_id": conversation.pk,
                "user_message_id": user_message.pk,
                "message_id": assistant_message.pk,
                "reply": assistant_message.content,
                "response": assistant_message.content,
                "source": assistant_message.source_label,
                "fallback": assistant_message.is_fallback,
                "mode": "fallback" if assistant_message.is_fallback else "provider",
                "expert_url": "/farmer/consultations/experts/" if request.user.role == "FARMER" else None,
            }
        )


class NewConversationView(LoginRequiredMixin, View):
    def post(self, request):
        conversation = AIConversation.objects.create(user=request.user)
        request.session["ai_conversation_id"] = conversation.pk
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"conversation_id": conversation.pk}, status=201)
        return redirect(f"{reverse('ai_assistant:panel')}?conversation={conversation.pk}")
