"""Zhihu adapter via opencli."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, write_text, now_iso

log = logging.getLogger(__name__)


def _extract_zhihu_id(url: str) -> str:
    m = re.search(r"question/(\d+)", url)
    if m:
        return f"q_{m.group(1)}"
    m = re.search(r"answer/(\d+)", url)
    if m:
        return f"a_{m.group(1)}"
    m = re.search(r"p/(\d+)", url)
    if m:
        return f"p_{m.group(1)}"
    return url.rstrip("/").split("/")[-1]


def _detect_content_type(url: str) -> str:
    if "question" in url:
        return "topic"
    if "/p/" in url:
        return "article"
    return "article"


class ZhihuAdapter(PlatformAdapter, adapter_name="zhihu"):
    URL_PATTERNS = ["zhihu.com"]

    def search(self, query: str, limit: int = 20) -> list[str]:
        results = run_opencli("zhihu", "search", [query, "--limit", str(limit)])
        return [item["url"] for item in results if "url" in item]

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        zhihu_id = _extract_zhihu_id(url)
        content_type = _detect_content_type(url)

        try:
            raw = run_opencli("zhihu", "question", [url])
        except Exception as e:
            return FetchResult("error", content_type, output_dir, False, error=str(e))

        if isinstance(raw, list) and raw:
            info = raw[0] if isinstance(raw[0], dict) else {}
            content = info.get("content", info.get("answer", ""))
        elif isinstance(raw, dict):
            info = raw
            content = raw.get("content", raw.get("answer", ""))
        else:
            info = {}
            content = str(raw)

        write_text(output_dir / "content.md", content)

        comments = []
        log.warning("Zhihu comments not available via opencli for %s", url)
        write_json(output_dir / "comments.json", comments)

        from datetime import datetime, timedelta, timezone
        refresh_state = {
            "current_interval_days": 14,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": 0,
        }

        meta = {
            "id": zhihu_id,
            "platform": "zhihu",
            "url": url,
            "content_type": content_type,
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": info.get("title", ""),
            "author": info.get("author", ""),
            "published_at": info.get("created", ""),
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"content": "content.md", "comments": "comments.json", "assets": []},
            "comments_refresh": refresh_state,
            "comment_history": [],
            "platform_meta": {
                "voteup_count": info.get("voteup_count", ""),
                "answer_count": info.get("answer_count", ""),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", content_type, output_dir, False)

    def fetch_comments(self, url: str) -> list[dict]:
        log.warning("Zhihu comments not available via opencli")
        return []

    def import_file(self, file_path: Path, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        import json
        data = json.loads(file_path.read_text(encoding="utf-8"))

        content = data.get("content", "")
        write_text(output_dir / "content.md", content)
        write_json(output_dir / "comments.json", data.get("comments", []))

        meta = {
            "id": data.get("id", file_path.stem),
            "platform": "zhihu",
            "url": data.get("url", ""),
            "content_type": data.get("content_type", "article"),
            "fetch_method": "import",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": data.get("title", ""),
            "author": data.get("author", ""),
            "published_at": data.get("created", ""),
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"content": "content.md", "comments": "comments.json", "assets": []},
            "comments_refresh": None,
            "comment_history": [],
            "platform_meta": data.get("platform_meta", {}),
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "article", output_dir, False)
