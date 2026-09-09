"""JSON parser unit tests."""

from src.core.models import AssistantPersona
from src.utils.parsers import extract_json_from_response, parse_json_response


def test_extract_json_from_code_fence():
    text = 'Here you go:\n```json\n{"persona": "Analyst", "expertise": "AI", "approach": "Careful"}\n```'
    payload = extract_json_from_response(text)
    assert payload is not None
    assert payload["persona"] == "Analyst"


def test_parse_json_response_into_model():
    result = parse_json_response(
        '{"persona": "Research Analyst", "expertise": "General research", "approach": "Summarize"}',
        AssistantPersona,
    )
    assert result.persona == "Research Analyst"


def test_parse_json_response_uses_default_on_failure():
    default = AssistantPersona(
        persona="Research Analyst",
        expertise="General research and information synthesis",
        approach="Provide balanced, factual overview from multiple perspectives",
    )
    result = parse_json_response("not-json", AssistantPersona, default=default)
    assert result is default
