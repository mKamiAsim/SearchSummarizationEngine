"""JSON extraction helpers for LLM responses."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


def extract_json_from_response(response: str) -> dict[str, Any] | None:
    """Extract a JSON object from LLM response text."""
    try:
        parsed = json.loads(response)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    json_pattern = r"```(?:json)?\s*({[\s\S]*?})\s*```"
    matches = re.findall(json_pattern, response)
    if matches:
        try:
            parsed = json.loads(matches[0])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    json_pattern_simple = r"({[\s\S]*?})"
    matches = re.findall(json_pattern_simple, response)
    for match in matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    logger.warning("Failed to extract JSON from response: %s...", response[:200])
    return None


def parse_json_response(
    response: str,
    model: type[BaseModel],
    default: BaseModel | None = None,
) -> BaseModel:
    """Parse LLM JSON response into a Pydantic model."""
    json_dict = extract_json_from_response(response)

    if json_dict is None:
        if default is not None:
            logger.warning("JSON extraction failed, using default: %s", model.__name__)
            return default
        raise ValueError(f"Failed to extract JSON from response: {response[:200]}...")

    try:
        return model.model_validate(json_dict)
    except ValidationError as exc:
        logger.warning("Pydantic validation failed: %s", exc)
        if default is not None:
            return default
        raise
