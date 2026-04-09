"""Reddit adapter via opencli."""

from __future__ import annotations

import re
from pathlib import Path

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, maybe_write_text, maybe_write_json, now_iso


def _extract_post_id(url: str) -> str:
    m = re.search(r"/comments/([a-z0-9]+)", url)
    return f"t3_{m.group(1)}" if m else url.rstrip("/").split("/")[-1]


class RedditAdapter(PlatformAdapter, adapter_name="reddit"):
    URL_PATTERNS = ["reddit.com"]

    def search(self, query: str, limit: int = 20) -> list[str]:
        results = run_opencli("reddit", "search", [query, "--limit", str(limit)])
        return [item["url"] for item in results if "url" in item]

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        post_id = _extract_post_id(url)

        try:
            raw = run_opencli("reddit", "read", [url])
        except Exception as e:
            return FetchResult("error", "post", output_dir, False, error=str(e))

        if isinstance(raw, list) and raw:
            post_body = raw[0].get("body", raw[0].get("text", ""))
            comments = raw[1:] if len(raw) > 1 else []
        elif isinstance(raw, dict):
            post_body = raw.get("body", raw.get("text", ""))
            comments = raw.get("comments", [])
        else:
            post_body = str(raw)
            comments = []

        content_file = maybe_write_text(output_dir / "content.md", post_body)
        comments_file = maybe_write_json(output_dir / "comments.json", comments)

        from datetime import datetime, timedelta, timezone
        refresh_state = {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": len(comments),
        }

        title = ""
        author = ""
        if isinstance(raw, list) and raw:
            title = raw[0].get("title", "")
            author = raw[0].get("author", "")
        elif isinstance(raw, dict):
            title = raw.get("title", "")
            author = raw.get("author", "")

        files: dict = {"assets": []}
        if content_file:
            files["content"] = content_file
        if comments_file:
            files["comments"] = comments_file

        meta = {
            "id": post_id,
            "platform": "reddit",
            "url": url,
            "content_type": "post",
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": title,
            "author": author,
            "published_at": "",
            "language": "en",
            "content_fetched": bool(post_body and post_body.strip()),
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": files,
            "comments_refresh": refresh_state,
            "comment_history": [{"timestamp": now_iso(), "count": len(comments)}],
            "platform_meta": {
                "subreddit": "",
                "score": "",
                "num_comments": len(comments),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "post", output_dir, False)

    def fetch_comments(self, url: str) -> list[dict]:
        raw = run_opencli("reddit", "read", [url])
        if isinstance(raw, list) and len(raw) > 1:
            return raw[1:]
        if isinstance(raw, dict):
            return raw.get("comments", [])
        return []
