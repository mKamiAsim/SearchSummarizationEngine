"""Utils module with web scraping, searching, and logging utilities."""

from .logging_config import setup_logging, get_logger, LogContext
from .time_context import get_time_context, is_historical_query
from .web_searching import search_web, search_multiple_queries
from .web_scraping import scrape_url, scrape_urls

__all__ = [
    "setup_logging",
    "get_logger",
    "LogContext",
    "get_time_context",
    "is_historical_query",
    "search_web",
    "search_multiple_queries",
    "scrape_url",
    "scrape_urls",
]
