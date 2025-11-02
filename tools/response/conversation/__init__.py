"""Conversational response tool built on top of the ConversationManager."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:  # pragma: no cover
    from conversation_manager import ConversationManager

from personas import get_persona_config


logger = logging.getLogger(__name__)


class ConversationalResponseTool:
    """Tool responsible for generating conversational text responses."""

    def __init__(self, manager: Optional["ConversationManager"] = None) -> None:
        if manager is None:
            from conversation_manager import ConversationManager  # local import to avoid circular

            self.manager = ConversationManager()
        else:
            self.manager = manager

    def _apply_persona(
        self,
        session_data: Dict[str, Any],
        persona_name: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Ensure session has persona metadata and return config."""
        persona_config = get_persona_config(persona_name or session_data.get("persona"))
        session_data["persona"] = persona_config["id"]
        return session_data, persona_config

    def create_session(
        self,
        customer_id: Optional[str] = None,
        persona: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new conversation session structure."""
        session = self.manager.create_session(customer_id)
        session, persona_config = self._apply_persona(session, persona)
        logger.info("Created conversation session for customer_id=%s", customer_id)
        logger.debug("Persona applied to session: %s", persona_config["id"])
        return session

    async def generate_response(
        self,
        session_data: Dict[str, Any],
        user_input: str,
        persona: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process user input through the conversation manager."""
        if not user_input:
            return {
                "session_data": session_data,
                "response": "I'm sorry, I didn't catch that. Could you repeat?",
                "next_state": session_data.get("state"),
                "actions": [],
                "persona": session_data.get("persona"),
            }

        session_data, persona_config = self._apply_persona(session_data, persona)
        result = await self.manager.process_user_input(
            session_data,
            user_input,
            persona_config,
        )
        result.setdefault("persona", session_data.get("persona"))
        logger.info("Generated conversational response for input: %s", user_input[:80])
        return result

    def summarize_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a lightweight summary of the current session."""
        summary = self.manager.get_session_summary(session_data)
        logger.debug("Session summary: %s", summary)
        return summary

