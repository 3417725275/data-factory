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

        if content_type == "article":
            return self._fetch_article(url, output_dir, zhihu_id)

        return self._fetch_question(url, output_dir, zhihu_id, content_type)

    def _fetch_article(self, url: str, output_dir: Path, zhihu_id: str) -> FetchResult:
        """Fetch a zhihu zhuanlan article using opencli zhihu download."""
        try:
            raw = run_opencli("zhihu", "download", [
                "--url", url,
                "--output", str(output_dir / "assets"),
            ])
        except Exception as e:
            return FetchResult("error", "article", output_dir, False, error=str(e))

        info = {}
        content = ""
        if isinstance(raw, list) and raw:
            info = raw[0] if isinstance(raw[0], dict) else {}
        elif isinstance(raw, dict):
            info = raw

        md_files = list((output_dir / "assets").rglob("*.md")) if (output_dir / "assets").exists() else []
        if md_files:
            content = md_files[0].read_text(encoding="utf-8")
        elif info:
            content = info.get("content", info.get("title", ""))

        write_text(output_dir / "content.md", content)
        write_json(output_dir / "comments.json", [])

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
            "content_type": "article",
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": info.get("title", ""),
            "author": info.get("author", ""),
            "published_at": info.get("publish_time", ""),
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"content": "content.md", "comments": "comments.json", "assets": []},
            "comments_refresh": refresh_state,
            "comment_history": [],
            "platform_meta": {
                "article_id": zhihu_id,
                "size": info.get("size", ""),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "article", output_dir, False)

    def _fetch_question(self, url: str, output_dir: Path, zhihu_id: str, content_type: str) -> FetchResult:
        """Fetch a zhihu question using opencli zhihu question <numeric_id>."""
        m = re.search(r"question/(\d+)", url)
        if not m:
            return FetchResult("error", content_type, output_dir, False,
                               error=f"Cannot extract numeric question ID from: {url}")
        question_id = m.group(1)

        try:
            raw = run_opencli("zhihu", "question", [question_id, "--limit", "10"])
        except Exception as e:
            return FetchResult("error", content_type, output_dir, False, error=str(e))

        answers = []
        if isinstance(raw, list):
            answers = [r for r in raw if isinstance(r, dict)]
        elif isinstance(raw, dict):
            answers = [raw]

        parts = []
        authors = []
        for ans in answers:
            author = ans.get("author", "anonymous")
            votes = ans.get("votes", 0)
            text = ans.get("content", "")
            authors.append(author)
            parts.append(f"## 回答 by {author} (赞同: {votes})\n\n{text}")

        content = f"# 知乎问题 {question_id}\n\n" + "\n\n---\n\n".join(parts) if parts else ""
        write_text(output_dir / "content.md", content)

        write_json(output_dir / "answers.json", answers)

        comments = []
        log.warning("Zhihu comments not available via opencli for %s", url)
        write_json(output_dir / "comments.json", comments)

        first = answers[0] if answers else {}
        first_content = first.get("content", "")
        title = first_content[:80].replace("\n", " ") if first_content else f"问题 {question_id}"

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
            "title": title,
            "author": authors[0] if authors else "",
            "published_at": "",
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"content": "content.md", "answers": "answers.json", "comments": "comments.json", "assets": []},
            "comments_refresh": refresh_state,
            "comment_history": [],
            "platform_meta": {
                "question_id": question_id,
                "answer_count": len(answers),
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
