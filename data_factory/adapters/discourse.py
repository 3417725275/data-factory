"""Discourse adapter via native JSON API (no opencli)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import requests

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, maybe_write_text, maybe_write_json, now_iso

log = logging.getLogger(__name__)


def _extract_topic_id(url: str) -> str:
    m = re.search(r"/t/[^/]+/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/t/(\d+)", url)
    return m.group(1) if m else url.rstrip("/").split("/")[-1]


class DiscourseAdapter(PlatformAdapter, adapter_name="discourse"):
    URL_PATTERNS = []

    def __init__(self, base_url: str = "", platform_key: str = "discourse", proxy: str = ""):
        self.base_url = base_url.rstrip("/")
        self.platform_key = platform_key
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def can_fetch(self, url: str) -> bool:
        if self.base_url and self.base_url in url:
            return True
        return False

    def search(self, query: str, limit: int = 20) -> list[str]:
        resp = self.session.get(f"{self.base_url}/search.json", params={"q": query}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        topics = data.get("topics", [])[:limit]
        return [f"{self.base_url}/t/{t['slug']}/{t['id']}" for t in topics]

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        topic_id = _extract_topic_id(url)

        try:
            resp = self.session.get(f"{self.base_url}/t/{topic_id}.json", timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return FetchResult("error", "topic", output_dir, False, error=str(e))

        posts = data.get("post_stream", {}).get("posts", [])
        first_post = posts[0] if posts else {}
        comments = posts[1:] if len(posts) > 1 else []

        content = first_post.get("cooked", "")
        content_file = maybe_write_text(output_dir / "content.html", content)
        posts_file = maybe_write_json(output_dir / "posts.json", posts)
        comments_file = maybe_write_json(output_dir / "comments.json", comments)

        from datetime import datetime, timedelta, timezone

        refresh_state = {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": len(comments),
        }

        files: dict = {"assets": []}
        if content_file:
            files["content"] = content_file
        if posts_file:
            files["posts"] = posts_file
        if comments_file:
            files["comments"] = comments_file

        meta = {
            "id": topic_id,
            "platform": self.platform_key,
            "url": url,
            "content_type": "topic",
            "fetch_method": "api",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": data.get("title", ""),
            "author": first_post.get("username", ""),
            "published_at": first_post.get("created_at", ""),
            "language": "",
            "content_fetched": bool(content and content.strip()),
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": files,
            "comments_refresh": refresh_state,
            "comment_history": [{"timestamp": now_iso(), "count": len(comments)}],
            "platform_meta": {
                "category": data.get("category_id", ""),
                "views": data.get("views", 0),
                "reply_count": data.get("reply_count", 0),
                "like_count": data.get("like_count", 0),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "topic", output_dir, False)

    def fetch_comments(self, url: str) -> list[dict]:
        topic_id = _extract_topic_id(url)
        resp = self.session.get(f"{self.base_url}/t/{topic_id}.json", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        posts = data.get("post_stream", {}).get("posts", [])
        return posts[1:] if len(posts) > 1 else []
