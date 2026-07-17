from __future__ import annotations

from .config import settings


def build_search_tools():
    """Return optional web-search tools for agents that need external context.

    Keep this separate so you can later swap Google Search for Tavily, Serper,
    a private search API, or no search at all.
    """

    if not settings.enable_web_search:
        return []

    from google.adk.tools import google_search

    return [google_search]
