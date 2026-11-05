import logging
from dataclasses import dataclass

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssistantResult:
    content: str
    source_label: str
    is_fallback: bool


FALLBACK_TOPICS = {
    "irrig": (
        "Check soil moisture before irrigating, water during cooler hours, and match the amount to crop stage and soil drainage. "
        "Avoid a fixed schedule after heavy rain. A local Agriculturalist can verify the plan for your field."
    ),
    "rain": (
        "Compare recent and historical rainfall with the crop's growth stage. Clear drainage before heavy rain and avoid applying "
        "fertilizer immediately before a downpour. Use the Weather & Alerts page for time-stamped local conditions."
    ),
    "soil": (
        "Start with a soil test where available, keep soil covered, add well-decomposed organic matter, and avoid working saturated soil. "
        "Recommendations vary by soil type, crop, and local conditions."
    ),
    "crop": (
        "Crop choice should consider season, soil, water access, local disease pressure, market needs, and verified historical conditions. "
        "Try the Farm Simulator for a transparent rule-based comparison, then ask a qualified Agriculturalist before a costly decision."
    ),
    "heat": (
        "During sustained heat, monitor soil moisture, irrigate at cooler times when appropriate, protect young plants, and watch for heat stress. "
        "Follow official local alerts and seek expert advice for crop-specific action."
    ),
}


def fallback_reply(message):
    lowered = message.lower()
    for keyword, response in FALLBACK_TOPICS.items():
        if keyword in lowered:
            return AssistantResult(
                content=response + " This is general decision support, not a yield guarantee.",
                source_label="Built-in agricultural guidance (AI provider not configured)",
                is_fallback=True,
            )
    return AssistantResult(
        content=(
            "I can help explain rainfall history, crop comparisons, irrigation, soil management, and weather preparation. "
            "Ask one focused question and include the crop and season if useful. For field-specific decisions, use Ask an Expert."
        ),
        source_label="Built-in agricultural guidance (AI provider not configured)",
        is_fallback=True,
    )


def _provider_endpoint():
    endpoint = settings.AI_API_BASE_URL.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint = f"{endpoint}/chat/completions"
    return endpoint


def provider_is_configured():
    return bool(settings.AI_API_KEY and settings.AI_API_BASE_URL and settings.AI_MODEL)


def generate_reply(*, user, message, recent_messages=()):
    cleaned = " ".join(message.split()).strip()
    if not cleaned:
        raise ValueError("A message is required.")
    if len(cleaned) > 1500:
        raise ValueError("Messages must be 1,500 characters or fewer.")
    if not provider_is_configured():
        return fallback_reply(cleaned)

    history = []
    for item in list(recent_messages)[-8:]:
        history.append({"role": "user" if item.role == "USER" else "assistant", "content": item.content[:3000]})
    system_prompt = (
        "You are Farm Time Machine's agricultural decision-support assistant. Give concise, cautious, practical guidance. "
        "Never claim guaranteed yield or certainty. State important uncertainty and suggest verified data or a qualified Agriculturalist. "
        "Do not request unnecessary personal information. The user's district may be used only as broad location context."
    )
    if user.district:
        system_prompt += f" Broad district context: {user.district}."
    payload = {
        "model": settings.AI_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": cleaned}],
        "temperature": 0.2,
        "max_tokens": 500,
    }
    try:
        response = requests.post(
            _provider_endpoint(),
            headers={"Authorization": f"Bearer {settings.AI_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=(3.05, 12),
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        if not content:
            raise ValueError("The provider returned an empty response")
        return AssistantResult(content=content, source_label=f"AI provider: {settings.AI_MODEL}", is_fallback=False)
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("AI provider unavailable: %s", exc.__class__.__name__)
        result = fallback_reply(cleaned)
        return AssistantResult(
            content=result.content,
            source_label="Built-in guidance (AI provider temporarily unavailable)",
            is_fallback=True,
        )
