from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from config import RELAX_QUERIES, RELAX_QUERY_TIERS


class YouTubeResolver:
    """Resolve watch URLs from queries with robust fallback."""

    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}
        self._youtube_reachability_checked = False
        self._youtube_reachable = False
        self._request_timeout_seconds = self._read_timeout_seconds()
        self._local_only = os.getenv("AB_RELAX_LOCAL_ONLY", "0") == "1"

    @staticmethod
    def _read_timeout_seconds() -> float:
        raw = os.getenv("AB_RELAX_RESOLVE_TIMEOUT_SECONDS", "2.4").strip()
        try:
            value = float(raw)
        except Exception:
            return 2.4
        return max(0.8, min(value, 8.0))

    @staticmethod
    def _search_results_fallback(query: str) -> str:
        return f"https://www.youtube.com/results?search_query={quote_plus(query)}"

    @staticmethod
    def _local_relax_fallback() -> str:
        return (Path(__file__).resolve().parent / "assets" / "relax.html").as_uri()

    @staticmethod
    def _watch_url(video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"

    @staticmethod
    def _request_headers() -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            )
        }

    def _can_reach_youtube(self) -> bool:
        if self._youtube_reachability_checked:
            return self._youtube_reachable

        self._youtube_reachability_checked = True
        probe = Request("https://www.youtube.com/generate_204", headers=self._request_headers())
        try:
            with urlopen(probe, timeout=min(2.0, self._request_timeout_seconds)):
                self._youtube_reachable = True
        except Exception:
            self._youtube_reachable = False
        return self._youtube_reachable

    def _resolve_via_search_html(self, query: str) -> str | None:
        """Fetch YouTube results HTML and extract first videoId."""
        if self._local_only or not self._can_reach_youtube():
            return None

        url = self._search_results_fallback(query)
        req = Request(url, headers=self._request_headers())

        try:
            with urlopen(req, timeout=self._request_timeout_seconds) as resp:
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

    @staticmethod
    def _url_count_for_stage(stage: int) -> int:
        if stage <= 1:
            return 1
        if stage <= 3:
            return 2
        return 3

    @staticmethod
    def _stage_hint(stage: int) -> str:
        if stage <= 0:
            return "natureza relaxante anti-burnout"
        if stage == 1:
            return "ambiente calmante anti-burnout"
        if stage == 2:
            return "satisfying visual anti-burnout"
        if stage == 3:
            return "meme caos anti-burnout"
        return "shitpost dopamina forcada anti-burnout"

    def _queries_for_stage(self, stage: int) -> List[str]:
        tiers = [tier for tier in RELAX_QUERY_TIERS if tier]
        if not tiers:
            return RELAX_QUERIES or ["relaxing nature scenery 4k"]

        tier_idx = min(max(0, stage), len(tiers) - 1)
        return tiers[tier_idx]

    def resolve_for_mode(self, *, media_level: int, madness_stage: int, max_urls: int) -> Tuple[List[str], str]:
        queries = self._queries_for_stage(madness_stage)
        count = max(1, min(max_urls, self._url_count_for_stage(madness_stage)))
        if not queries:
            return [self._local_relax_fallback()], self._stage_hint(madness_stage)

        urls: List[str] = []
        stage = max(0, madness_stage)
        base = (max(0, media_level) * 3) + (stage * 5) + ((stage // 2) * 3)
        for i in range(count):
            query = queries[(base + i) % len(queries)]
            urls.append(self._resolve_query(query))
        return urls, self._stage_hint(madness_stage)

    def hint_for_stage(self, stage: int) -> str:
        return self._stage_hint(stage)

    def resolve_for_level(self, level: int) -> List[str]:
        """Backward-compatible method."""
        urls, _ = self.resolve_for_mode(media_level=level, madness_stage=0, max_urls=3)
        return urls
