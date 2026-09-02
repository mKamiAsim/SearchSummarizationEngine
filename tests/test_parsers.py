from langchain_core.runnables import Runnable

from src.core.models import AssistantPersona
from src.utils.parsers import RobustPydanticParser


def test_robust_pydantic_parser_is_runnable():
    parser = RobustPydanticParser(
        model=AssistantPersona,
        default=AssistantPersona(
            persona="Research Analyst",
            expertise="General research and information synthesis",
            approach="Provide balanced, factual overview from multiple perspectives",
        ),
        max_retries=1,
    )

    assert isinstance(parser, Runnable)
    parsed = parser.parse(
        '{"persona": "Research Analyst", "expertise": "General research", "approach": "Summarize"}')
    assert parsed.persona == "Research Analyst"
