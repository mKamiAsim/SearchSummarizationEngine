"""
Output parsers and validators for LLM responses.

This module provides robust parsing of LLM outputs, especially JSON responses,
with fallback mechanisms and validation.
"""

import json
import logging
import re
from typing import Any

from langchain_core.output_parsers import BaseOutputParser, PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, ValidationError, Field, model_validator

logger = logging.getLogger(__name__)


def extract_json_from_response(response: str) -> dict[str, Any] | None:
    """
    Extract JSON object from LLM response text.

    LLMs sometimes include explanatory text before/after JSON.
    This function extracts the JSON portion.

    Args:
        response: Raw LLM response text

    Returns:
        dict | None: Parsed JSON dict, or None if parsing fails
    """
    # Try parsing as-is first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Look for JSON object in code blocks
    json_pattern = r"```(?:json)?\s*({[\s\S]*?})\s*```"
    matches = re.findall(json_pattern, response)

    if matches:
        try:
            return json.loads(matches[0])
        except json.JSONDecodeError:
            pass

    # Look for JSON object without code blocks
    json_pattern_simple = r"({[\s\S]*?})"
    matches = re.findall(json_pattern_simple, response)

    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    logger.warning(
        f"Failed to extract JSON from response: {response[:200]}...")
    return None


def parse_json_response(
    response: str,
    model: type[BaseModel],
    default: BaseModel | None = None,
) -> BaseModel:
    """
    Parse LLM JSON response into a Pydantic model.

    This is a robust parser that handles malformed JSON and provides
    sensible defaults on failure.

    Args:
        response: Raw LLM response text
        model: Pydantic model class to parse into
        default: Default instance to return on parsing failure

    Returns:
        BaseModel: Parsed model instance

    Raises:
        ValueError: If parsing fails and no default provided
    """
    # Extract JSON from response
    json_dict = extract_json_from_response(response)

    if json_dict is None:
        if default is not None:
            logger.warning(
                f"JSON extraction failed, using default: {model.__name__}")
            return default
        raise ValueError(
            f"Failed to extract JSON from response: {response[:200]}...")

    # Validate against Pydantic model
    try:
        return model.model_validate(json_dict)
    except ValidationError as e:
        logger.warning(f"Pydantic validation failed: {e}")
        if default is not None:
            return default
        raise


class RobustPydanticParser(BaseOutputParser[BaseModel]):
    """
    Robust output parser for Pydantic models with fallback.

    This parser combines LangChain's PydanticOutputParser with
    custom error handling and default values. Fully LCEL compatible.
    """

    # 1. Properly define Pydantic schema types
    model: type[BaseModel]
    default: BaseModel | None = None
    max_retries: int = 3

    # Exclude from direct init signature or mark as optionally computed
    langchain_parser: Any = None

    # 2. Use a Pydantic model validator instead of a custom __init__
    @model_validator(mode="after")
    def setup_langchain_parser(self) -> "RobustPydanticParser":
        if self.langchain_parser is None:
            self.langchain_parser = PydanticOutputParser(
                pydantic_object=self.model)
        return self

    def parse(self, text: Any) -> BaseModel:
        """
        Parse LLM response string into Pydantic model.
        """
        # Safely capture string if data arrives as a LangChain Message object
        input_string = text.content if hasattr(text, "content") else str(text)

        for attempt in range(self.max_retries):
            try:
                # Try LangChain's parser first
                return self.langchain_parser.parse(input_string)
            except OutputParserException:
                pass

            # Fall back to custom parser
            try:
                return parse_json_response(input_string, self.model, self.default)
            except ValueError:
                pass

            if attempt < self.max_retries - 1:
                logger.warning(
                    f"Parse attempt {attempt + 1}/{self.max_retries} failed, retrying..."
                )

        # All retries failed
        if self.default is not None:
            logger.error("All parsing attempts failed, using default")
            return self.default

        raise OutputParserException(
            f"Failed to parse response after {self.max_retries} attempts"
        )

    def get_format_instructions(self) -> str:
        """Get format instructions for the prompt."""
        return self.langchain_parser.get_format_instructions()

    @property
    def _type(self) -> str:
        return "robust_pydantic_parser"
