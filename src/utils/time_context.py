"""Current-date context and historical-query detection for research prompts."""

from __future__ import annotations

import re
from datetime import date

_HISTORICAL_INTENT = re.compile(
    r"\b("
    r"history|historical|evolution|timeline|"
    r"over the years|through the years|"
    r"since\s+20\d{2}|from\s+20\d{2}|between\s+20\d{2}"
    r")\b",
    re.IGNORECASE,
)


def get_time_context(today: date | None = None) -> dict[str, str]:
    """Return prompt variables for the current calendar date.

    Args:
        today: Optional date override (useful in tests). Defaults to date.today().

    Returns:
        dict with current_date (e.g. "Thursday, 03 September 2026") and current_year.
    """
    today = today or date.today()
    return {
        "current_date": today.strftime("%A, %d %B %Y"),
        "current_year": str(today.year),
    }


def is_historical_query(user_question: str, today: date | None = None) -> bool:
    """True only when the user explicitly asks for a past period.

    Latest / current research is the default. A past year in the question, or
    clear history language, opts out of recency filtering.
    """
    if not user_question or not user_question.strip():
        return False

    today = today or date.today()
    years = [int(year) for year in re.findall(r"\b(20\d{2})\b", user_question)]
    if any(year < today.year for year in years):
        return True

    return bool(_HISTORICAL_INTENT.search(user_question))
