"""Bilibili adapter via opencli."""

from __future__ import annotations

import re
from pathlib import Path

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, write_text, now_iso


def download_file(url: str, dest: Path, **kwargs) -> bool:
    import requests
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return True
    except Exception:
        return False


def _extract_bvid(url: str) -> str:
    m = re.search(r"(BV[a-zA-Z0-9]+)", url)
    return m.group(1) if m else url.rstrip("/").split("/")[-1]


def _field_value_to_dict(rows: list[dict]) -> dict[str, str]:
    out = {}
    for row in rows:
        key = row.get("field", "").lower().replace(" ", "_")
        out[key] = row.get("value", "")
    return out


class BilibiliAdapter(PlatformAdapter, adapter_name="bilibili"):
    URL_PATTERNS = ["bilibili.com", "b23.tv"]

    def search(self, query: str, limit: int = 20) -> list[str]:
        results = run_opencli("bilibili", "search", [query, "--limit", str(limit)])
        return [item["url"] for item in results if "url" in item]

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        bvid = _extract_bvid(url)

        try:
            raw_info = run_opencli("bilibili", "search", [bvid, "--limit", "1"])
            if isinstance(raw_info, list) and raw_info and "field" in raw_info[0]:
                info = _field_value_to_dict(raw_info)
            elif isinstance(raw_info, list) and raw_info:
                info = raw_info[0]
            else:
                info = {}
        except Exception as e:
            return FetchResult("error", "video", output_dir, False, error=str(e))

        description = info.get("description", "")
        write_text(output_dir / "description.txt", description)

        try:
            comments = self.fetch_comments(url)
        except Exception:
            comments = []
        write_json(output_dir / "comments.json", comments)

        from datetime import datetime, timedelta, timezone
        refresh_state = {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": len(comments),
        }

        meta = {
            "id": bvid,
            "platform": "bilibili",
            "url": url,
            "content_type": "video",
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "draft",
            "title": info.get("title", ""),
            "author": info.get("author", info.get("up主", "")),
            "published_at": info.get("published", ""),
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"description": "description.txt", "comments": "comments.json", "assets": []},
            "comments_refresh": refresh_state,
            "comment_history": [{"timestamp": now_iso(), "count": len(comments)}],
            "platform_meta": {
                "bvid": bvid,
                "views": info.get("views", ""),
                "likes": info.get("likes", ""),
                "duration": info.get("duration", ""),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "video", output_dir, True)

    def fetch_comments(self, url: str) -> list[dict]:
        bvid = _extract_bvid(url)
        return run_opencli("bilibili", "comments", [bvid, "--limit", "50"])
