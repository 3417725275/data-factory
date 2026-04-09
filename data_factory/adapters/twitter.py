"""Twitter/X adapter via opencli."""

from __future__ import annotations

import re
from pathlib import Path

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, write_text, now_iso


def _extract_tweet_id(url: str) -> str:
    m = re.search(r"status/(\d+)", url)
    return m.group(1) if m else url.rstrip("/").split("/")[-1]


class TwitterAdapter(PlatformAdapter, adapter_name="twitter"):
    URL_PATTERNS = ["twitter.com", "x.com"]

    def search(self, query: str, limit: int = 20) -> list[str]:
        results = run_opencli("twitter", "search", [query, "--limit", str(limit)])
        return [item["url"] for item in results if "url" in item]

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        tweet_id = _extract_tweet_id(url)

        try:
            raw = run_opencli("twitter", "thread", [tweet_id])
        except Exception as e:
            return FetchResult("error", "post", output_dir, False, error=str(e))

        if isinstance(raw, list) and raw:
            main_tweet = raw[0] if isinstance(raw[0], dict) else {}
            replies = raw[1:] if len(raw) > 1 else []
        elif isinstance(raw, dict):
            main_tweet = raw
            replies = raw.get("replies", [])
        else:
            main_tweet = {}
            replies = []

        content = main_tweet.get("text", main_tweet.get("content", ""))
        write_text(output_dir / "content.txt", content)
        write_json(output_dir / "comments.json", replies)

        try:
            run_opencli("twitter", "download", ["--tweet-url", url, "--output", str(assets_dir)])
        except Exception:
            pass

        from datetime import datetime, timedelta, timezone

        refresh_state = {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": len(replies),
        }

        meta = {
            "id": tweet_id,
            "platform": "twitter",
            "url": url,
            "content_type": "post",
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": content[:80] if content else "",
            "author": main_tweet.get("author", main_tweet.get("username", "")),
            "published_at": main_tweet.get("time", ""),
            "language": "",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"content": "content.txt", "comments": "comments.json", "assets": []},
            "comments_refresh": refresh_state,
            "comment_history": [{"timestamp": now_iso(), "count": len(replies)}],
            "platform_meta": {
                "likes": main_tweet.get("likes", ""),
                "retweets": main_tweet.get("retweets", ""),
                "replies_count": len(replies),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "post", output_dir, False)

    def fetch_comments(self, url: str) -> list[dict]:
        tweet_id = _extract_tweet_id(url)
        raw = run_opencli("twitter", "thread", [tweet_id])
        if isinstance(raw, list) and len(raw) > 1:
            return raw[1:]
        if isinstance(raw, dict):
            return raw.get("replies", [])
        return []
