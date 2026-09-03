"""
Web scraping utilities using BeautifulSoup and requests.

This module provides robust web scraping with error handling,
content extraction, and text cleaning.
"""

import logging
from html import unescape
from typing import Any

import html2text
import requests
from bs4 import BeautifulSoup
from langsmith import traceable

from ..config.settings import Settings, get_settings
from ..core.models import ScrapedContent

logger = logging.getLogger(__name__)

# Common HTML tags to skip when extracting text
SKIP_TAGS = {"script", "style", "nav", "footer", "header", "noscript"}

# HTTP headers to mimic browser requests
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


@traceable(name="scrape_url", run_type="tool", process_inputs=lambda inputs: {k: v for k, v in inputs.items() if k != "settings"})
def scrape_url(
    url: str,
    max_characters: int = 10000,
    settings: Settings | None = None,
) -> ScrapedContent:
    """
    Scrape and extract text content from a web page.

    Args:
        url: URL to scrape
        max_characters: Maximum characters to extract (truncate if longer)
        settings: Settings instance

    Returns:
        ScrapedContent: Extracted content with metadata

    Example:
        >>> content = scrape_url("https://example.com/article", max_characters=5000)
        >>> print(content.title)
        >>> print(content.content[:500])
    """
    if settings is None:
        settings = get_settings()

    logger.debug(f"Scraping URL: {url}")

    try:
        # Fetch the page
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=settings.scraper_timeout_seconds,
            allow_redirects=True,
        )
        response.raise_for_status()

        # Extract text content
        content = extract_text_from_html(response.text, url)

        # Truncate if necessary
        if len(content) > max_characters:
            logger.debug(
                f"Truncating content from {len(content)} to {max_characters} characters"
            )
            content = content[:max_characters] + "\n\n[Content truncated...]"

        # Extract title
        title = extract_title(response.text)

        scraped = ScrapedContent(
            url=url,
            content=content,
            title=title,
            success=True,
            content_length=len(content),
        )

        logger.info(
            f"Successfully scraped {url}: {len(content)} chars, title: '{title[:50]}...'"
        )
        return scraped

    except requests.exceptions.RequestException as e:
        logger.warning(f"HTTP error scraping {url}: {e}")
        return ScrapedContent(
            url=url,
            success=False,
            error_message=f"HTTP error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error scraping {url}: {e}", exc_info=True)
        return ScrapedContent(
            url=url,
            success=False,
            error_message=f"Scraping error: {str(e)}",
        )


@traceable(name="scrape_urls", run_type="tool", process_inputs=lambda inputs: {k: v for k, v in inputs.items() if k != "settings"})
def scrape_urls(
    urls: list[str],
    max_characters_per_url: int = 10000,
    max_concurrent: int = 5,
    settings: Settings | None = None,
) -> list[ScrapedContent]:
    """
    Scrape multiple URLs (sequentially for simplicity).

    For production, consider using asyncio/aiohttp for parallel scraping.

    Args:
        urls: List of URLs to scrape
        max_characters_per_url: Max characters per URL
        max_concurrent: Max concurrent scrapes (not used in sequential version)
        settings: Settings instance

    Returns:
        list[ScrapedContent]: List of scraped content from each URL
    """
    if settings is None:
        settings = get_settings()

    logger.info(f"Scraping {len(urls)} URLs...")

    results: list[ScrapedContent] = []
    success_count = 0

    for idx, url in enumerate(urls, start=1):
        logger.info(f"Scraping {idx}/{len(urls)}: {url}")

        content = scrape_url(
            url, max_characters=max_characters_per_url, settings=settings)
        results.append(content)

        if content.success:
            success_count += 1

    logger.info(
        f"Scraping complete: {success_count}/{len(urls)} successful, "
        f"{len(urls) - success_count} failed"
    )

    return results


def extract_text_from_html(html: str, url: str = "") -> str:
    """
    Extract clean text from HTML content.

    Uses html2text for conversion with custom optimizations.

    Args:
        html: Raw HTML content
        url: Source URL (for logging)

    Returns:
        str: Extracted plain text
    """
    try:
        # Configure html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = False
        h.body_width = 0  # Don't wrap text
        # h.escape_all = False
        h.escape_snob = True
        h.single_line_break = True

        # Convert HTML to text
        text = h.handle(html)

        # Clean up the text
        text = unescape(text)  # Handle HTML entities
        text = clean_text(text)

        return text.strip()

    except Exception as e:
        logger.warning(f"Failed to extract text from {url}: {e}")
        # Fallback: try simple BeautifulSoup extraction
        return extract_text_fallback(html, url)


def extract_text_fallback(html: str, url: str = "") -> str:
    """
    Fallback text extraction using BeautifulSoup only.

    Args:
        html: Raw HTML content
        url: Source URL

    Returns:
        str: Extracted text
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style tags
        for tag in soup.find_all(SKIP_TAGS):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)
        return clean_text(text)

    except Exception as e:
        logger.error(f"Fallback text extraction failed for {url}: {e}")
        return f"[Failed to extract content from {url}]"


def extract_title(html: str) -> str:
    """
    Extract page title from HTML.

    Args:
        html: Raw HTML content

    Returns:
        str: Page title or empty string
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Try <title> tag first
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return clean_text(title_tag.string)

        # Try <h1> tag
        h1_tag = soup.find("h1")
        if h1_tag:
            return clean_text(h1_tag.get_text())

        # Try og:title meta tag
        # meta_tag  = soup.find("meta", property="og:title")

        meta_tag = soup.find("meta", property="og:title")

        if meta_tag and meta_tag.has_attr("content"):
            # beautiful soup attributes can be strings or lists,
            # cast or join to guarantee a single flat string
            og_title = str(meta_tag["content"])
        else:
            og_title = ""

        return clean_text(og_title)

    except Exception as e:
        logger.debug(f"Failed to extract title: {e}")
        return ""


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text.

    Removes excessive whitespace, normalizes line breaks, etc.

    Args:
        text: Raw extracted text

    Returns:
        str: Cleaned text
    """
    import re

    # Replace multiple newlines with double newline
    text = re.sub(r"\n\s*\n", "\n\n", text)

    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)

    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove excessive blank lines (more than 2 consecutive)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
