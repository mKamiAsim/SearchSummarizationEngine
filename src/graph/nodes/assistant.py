"""Assistant selection node."""

from __future__ import annotations

import logging
from typing import Any

from ...config.settings import get_settings
from ...core.llm_factory import create_llm
from ...core.models import AssistantPersona
from ...utils.parsers import extract_json_from_response
from ..prompts import ASSISTANT_SELECTION_PROMPT
from ..state import ResearchGraphState

logger = logging.getLogger(__name__)


def select_assistant_node(state: ResearchGraphState) -> dict[str, Any]:
    """Select an expert persona for the research question."""
    user_question = state["user_question"]
    settings = get_settings()
    llm = create_llm(settings=settings)

    logger.info("Selecting assistant persona")
    prompt = ASSISTANT_SELECTION_PROMPT.format(user_question=user_question)

    default = AssistantPersona(
        persona="Research Analyst",
        expertise="General research and information synthesis",
        approach="Provide balanced, factual overview from multiple perspectives",
    )

    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        payload = extract_json_from_response(str(text)) or {}
        persona = AssistantPersona.model_validate(
            {
                "persona": payload.get("persona") or default.persona,
                "expertise": payload.get("expertise") or default.expertise,
                "approach": payload.get("approach") or default.approach,
            }
        )
    except Exception as exc:
        logger.warning("Assistant selection failed, using default: %s", exc)
        persona = default

    logger.info("Selected persona: %s", persona.persona)
    return {
        "assistant_persona": persona.model_dump(),
    }
