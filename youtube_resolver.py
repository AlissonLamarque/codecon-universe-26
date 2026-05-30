from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from config import RELAX_QUERIES


class YouTubeResolver:
    """Resolve watch URLs from queries with robust fallback."""

    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}

    @staticmethod
    def _search_results_fallback(query: str) -> str:
        return f"https://www.youtube.com/results?search_query={quote_plus(query)}"

    @staticmethod
    def _local_relax_fallback() -> str:
        return (Path(__file__).resolve().parent / "assets" / "relax.html").as_uri()

    @staticmethod
    def _watch_url(video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"

    def _resolve_via_search_html(self, query: str) -> str | None:
        """Fetch YouTube results HTML and extract first videoId."""
        url = self._search_results_fallback(query)
        req = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/127.0.0.0 Safari/537.36"
                )
            },
        )

        try:
            with urlopen(req, timeout=3) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

        ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        if not ids:
            return None

        # Keep first unique ID in order.
        first = ids[0]
        return self._watch_url(first)

    def _resolve_query(self, query: str) -> str:
        if query in self._cache:
            return self._cache[query]

        resolved = self._resolve_via_search_html(query)
        if resolved:
            self._cache[query] = resolved
            return resolved

        self._cache[query] = self._local_relax_fallback()
        return self._cache[query]

    def resolve_for_level(self, level: int) -> List[str]:
        """Higher levels open more tabs/videos."""
        if level < 3:
            count = 1
        elif level < 6:
            count = 2
        else:
            count = 3

        urls: List[str] = []
        for i in range(count):
            query = RELAX_QUERIES[(level + i) % len(RELAX_QUERIES)]
            urls.append(self._resolve_query(query))
        return urls
