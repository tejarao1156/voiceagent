"""Persona catalog defining conversational style and voice options."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


_PERSONAS: Dict[str, Dict[str, Any]] = {
    "friendly_guide": {
        "id": "friendly_guide",
        "display_name": "Friendly Guide",
        "description": "Warm, upbeat helper who keeps conversations light and encouraging.",
        "tts_voice": "verse",
        "tts_model": "gpt-4o-mini-tts",
        "conversation_prompt": (
            "Adopt a friendly, encouraging tone similar to a helpful tour guide. "
            "Use casual language, short sentences, and sprinkle in light encouragement."
        ),
        "realtime_voice": "verse",
    },
    "calm_concierge": {
        "id": "calm_concierge",
        "display_name": "Calm Concierge",
        "description": "Composed and professional concierge with steady pacing and clarity.",
        "tts_voice": "sol",
        "tts_model": "gpt-4o-mini-tts",
        "conversation_prompt": (
            "Respond like a seasoned hotel concierge: calm, articulate, and efficient. "
            "Favor clear explanations and reassure the customer with confident language."
        ),
        "realtime_voice": "sol",
    },
    "energetic_host": {
        "id": "energetic_host",
        "display_name": "Energetic Host",
        "description": "High-energy emcee who sounds excited and moves the conversation quickly.",
        "tts_voice": "alloy",
        "tts_model": "gpt-4o-realtime-preview-2024-12-17",
        "conversation_prompt": (
            "Channel an energetic event host. Keep a fast pace, express excitement, and "
            "build momentum in the conversation. Use lively, expressive phrasing."
        ),
        "realtime_voice": "alloy",
    },
}

_DEFAULT_PERSONA_KEY = "friendly_guide"


def get_persona_config(persona_name: Optional[str]) -> Dict[str, Any]:
    """Return persona configuration for the given name (fallback to default)."""

    if persona_name:
        key = persona_name.lower().strip()
        if key in _PERSONAS:
            return _PERSONAS[key]

    return _PERSONAS[_DEFAULT_PERSONA_KEY]


def list_personas() -> List[Dict[str, Any]]:
    """Return lightweight persona summaries suitable for API responses."""

    return [
        {
            "id": cfg["id"],
            "name": cfg["display_name"],
            "description": cfg["description"],
            "tts_voice": cfg.get("tts_voice"),
            "tts_model": cfg.get("tts_model"),
            "realtime_voice": cfg.get("realtime_voice"),
        }
        for cfg in _PERSONAS.values()
    ]


