"""Utils module with web scraping, searching, and logging utilities."""

from src.utils.logging_config import setup_logging, get_logger, LogContext
from src.utils.web_searching import search_web, search_multiple_queries
from src.utils.web_scraping import scrape_url, scrape_urls

__all__ = [
    "setup_logging",
    "get_logger",
    "LogContext",
    "search_web",
    "search_multiple_queries",
    "scrape_url",
    "scrape_urls",
]
