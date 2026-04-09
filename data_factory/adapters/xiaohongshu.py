"""Xiaohongshu adapter via opencli."""

from __future__ import annotations

import re
from pathlib import Path

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, write_text, now_iso


def _extract_note_id(url: str) -> str:
    m = re.search(r"(?:/explore/|note/)([a-f0-9]+)", url)
    return m.group(1) if m else url.rstrip("/").split("/")[-1]


class XiaohongshuAdapter(PlatformAdapter, adapter_name="xiaohongshu"):
    URL_PATTERNS = ["xiaohongshu.com", "xhslink.com"]

    def search(self, query: str, limit: int = 20) -> list[str]:
        results = run_opencli("xiaohongshu", "search", [query, "--limit", str(limit)])
        return [item["url"] for item in results if "url" in item]

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        note_id = _extract_note_id(url)

        try:
            raw_note = run_opencli("xiaohongshu", "note", [note_id])
        except Exception as e:
            return FetchResult("error", "post", output_dir, False, error=str(e))

        if isinstance(raw_note, list) and raw_note:
            info = raw_note[0] if isinstance(raw_note[0], dict) else {}
        elif isinstance(raw_note, dict):
            info = raw_note
        else:
            info = {}

        content = info.get("content", info.get("desc", ""))
        write_text(output_dir / "content.txt", content)

        try:
            comments = self.fetch_comments(url)
        except Exception:
            comments = []
        write_json(output_dir / "comments.json", comments)

        try:
            run_opencli("xiaohongshu", "download", [note_id, "--output", str(assets_dir)])
        except Exception:
            pass

        content_type = info.get("type", "post")
        if content_type not in ("video", "post"):
            content_type = "post"
        needs_transcribe = content_type == "video"

        from datetime import datetime, timedelta, timezone
        refresh_state = {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": len(comments),
        }

        meta = {
            "id": note_id,
            "platform": "xiaohongshu",
            "url": url,
            "content_type": content_type,
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "draft" if needs_transcribe else "complete",
            "title": info.get("title", ""),
            "author": info.get("author", info.get("nickname", "")),
            "published_at": info.get("time", ""),
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"content": "content.txt", "comments": "comments.json", "assets": []},
            "comments_refresh": refresh_state,
            "comment_history": [{"timestamp": now_iso(), "count": len(comments)}],
            "platform_meta": {
                "note_id": note_id,
                "likes": info.get("likes", ""),
                "collects": info.get("collects", ""),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", content_type, output_dir, needs_transcribe)

    def fetch_comments(self, url: str) -> list[dict]:
        note_id = _extract_note_id(url)
        return run_opencli("xiaohongshu", "comments", [note_id])

    def import_file(self, file_path: Path, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        import json
        data = json.loads(file_path.read_text(encoding="utf-8"))

        content = data.get("content", data.get("desc", ""))
        write_text(output_dir / "content.txt", content)
        write_json(output_dir / "comments.json", data.get("comments", []))

        meta = {
            "id": data.get("id", file_path.stem),
            "platform": "xiaohongshu",
            "url": data.get("url", ""),
            "content_type": "post",
            "fetch_method": "import",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": data.get("title", ""),
            "author": data.get("author", ""),
            "published_at": data.get("time", ""),
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"content": "content.txt", "comments": "comments.json", "assets": []},
            "comments_refresh": None,
            "comment_history": [],
            "platform_meta": data.get("platform_meta", {}),
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "post", output_dir, False)
