from unittest.mock import MagicMock, patch

import pytest

from src.config.settings import Settings
from src.utils.web_searching import resolve_search_backend, search_web


def _settings(**kwargs) -> Settings:
    defaults = {
        "search_backend": "tavily",
        "tavily_api_key": "tvly-test",
        "openai_api_key": "test",
    }
    defaults.update(kwargs)
    return Settings(**defaults)


def test_auto_backend_prefers_tavily_when_key_present():
    assert resolve_search_backend(_settings(search_backend="auto")) == "tavily"


def test_auto_backend_falls_back_without_key():
    assert (
        resolve_search_backend(_settings(search_backend="auto", tavily_api_key=""))
        == "duckduckgo"
    )


def test_tavily_requires_api_key():
    settings = _settings(search_backend="tavily", tavily_api_key="")
    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        search_web("Nvidia RTX Spark", settings=settings)


@patch("tavily.TavilyClient")
def test_tavily_maps_results_and_year_filter(mock_client_cls):
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "url": "https://nvidia.example/rtx-spark",
                "title": "NVIDIA RTX Spark",
                "content": "Desktop AI box launched in 2026.",
            }
        ]
    }
    mock_client_cls.return_value = mock_client

    results = search_web(
        "Nvidia RTX Spark vs Mac Studio M5",
        num_results=3,
        settings=_settings(),
        timelimit="y",
    )

    assert len(results) == 1
    assert results[0].url == "https://nvidia.example/rtx-spark"
    assert results[0].title == "NVIDIA RTX Spark"
    mock_client.search.assert_called_once()
    kwargs = mock_client.search.call_args.kwargs
    assert kwargs["query"] == "Nvidia RTX Spark vs Mac Studio M5"
    assert kwargs["max_results"] == 3
    assert kwargs["time_range"] == "year"
    assert kwargs["search_depth"] == "basic"
