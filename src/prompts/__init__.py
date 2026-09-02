"""
Prompts module - loads prompt templates from YAML files.

This module provides a centralized way to load and access prompt templates
used throughout the research engine pipeline.
"""

import logging
from functools import lru_cache
from pathlib import Path

import yaml
from langchain_core.prompts import PromptTemplate

from config.settings import get_settings

logger = logging.getLogger(__name__)


def _load_prompt_template(prompt_name: str) -> PromptTemplate:
    """
    Load a prompt template from YAML file.

    Args:
        prompt_name: Name of the prompt file (without .yaml extension)

    Returns:
        PromptTemplate: Loaded prompt template

    Raises:
        FileNotFoundError: If prompt file doesn't exist
        ValueError: If YAML is invalid or missing required fields
    """
    settings = get_settings()
    prompts_dir = settings.prompts_dir
    prompt_file = prompts_dir / f"{prompt_name}.yaml"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    logger.debug(f"Loading prompt template: {prompt_name}")

    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_data = yaml.safe_load(f)

    # Validate required fields
    if "template" not in prompt_data:
        raise ValueError(
            f"Prompt file missing 'template' field: {prompt_file}")

    # Extract input variables from YAML or infer from template
    input_variables = prompt_data.get("input_variables", [])
    if isinstance(input_variables, list) and len(input_variables) > 0:
        # Extract variable names from list of dicts
        var_names = [var["name"]
                     for var in input_variables if isinstance(var, dict)]
    else:
        # Fallback: let LangChain infer from template
        var_names = None

    # Create PromptTemplate
    template = PromptTemplate(
        template=prompt_data["template"],
        input_variables=var_names or [],
        name=prompt_data.get("name", prompt_name),
    )

    logger.debug(
        f"Loaded prompt template '{prompt_data.get('name', prompt_name)}' with {len(template.input_variables)} variables")

    return template


@lru_cache(maxsize=10)
def get_prompt_template(prompt_name: str) -> PromptTemplate:
    """
    Get a cached prompt template.

    This is the recommended way to load prompts. The template is cached
    to avoid repeated file I/O.

    Args:
        prompt_name: Name of the prompt (e.g., "assistant_selection")

    Returns:
        PromptTemplate: Loaded and cached prompt template

    Example:
        >>> prompt = get_prompt_template("assistant_selection")
        >>> formatted = prompt.format(user_question="What is quantum computing?")
    """
    return _load_prompt_template(prompt_name)


def get_all_prompts() -> dict[str, PromptTemplate]:
    """
    Load all available prompt templates.

    Returns:
        dict: Dictionary mapping prompt names to templates
    """
    settings = get_settings()
    prompts_dir = settings.prompts_dir

    prompts = {}
    for prompt_file in prompts_dir.glob("*.yaml"):
        prompt_name = prompt_file.stem
        try:
            prompts[prompt_name] = get_prompt_template(prompt_name)
        except Exception as e:
            logger.error(f"Failed to load prompt {prompt_name}: {e}")

    return prompts


# Convenience functions for specific prompts
def get_assistant_selection_prompt() -> PromptTemplate:
    """Get the assistant selection prompt template."""
    return get_prompt_template("assistant_selection")


def get_search_queries_prompt() -> PromptTemplate:
    """Get the search queries generation prompt template."""
    return get_prompt_template("search_queries")


def get_summarization_prompt() -> PromptTemplate:
    """Get the content summarization prompt template."""
    return get_prompt_template("summarization")


def get_report_compilation_prompt() -> PromptTemplate:
    """Get the report compilation prompt template."""
    return get_prompt_template("report_compilation")
