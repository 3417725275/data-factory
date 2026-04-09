"""TikTok adapter via opencli + yt-dlp."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, write_text, now_iso

log = logging.getLogger(__name__)


def _extract_tiktok_id(url: str) -> str:
    m = re.search(r"video/(\d+)", url)
    return m.group(1) if m else url.rstrip("/").split("/")[-1]


class TikTokAdapter(PlatformAdapter, adapter_name="tiktok"):
    URL_PATTERNS = ["tiktok.com"]

    def search(self, query: str, limit: int = 20) -> list[str]:
        results = run_opencli("tiktok", "search", [query, "--limit", str(limit)])
        return [item["url"] for item in results if "url" in item]

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        video_id = _extract_tiktok_id(url)

        try:
            raw = run_opencli("tiktok", "search", [url, "--limit", "1"])
        except Exception as e:
            return FetchResult("error", "video", output_dir, False, error=str(e))

        if isinstance(raw, list) and raw:
            info = raw[0] if isinstance(raw[0], dict) else {}
        elif isinstance(raw, dict):
            info = raw
        else:
            info = {}

        description = info.get("desc", info.get("description", ""))
        write_text(output_dir / "description.txt", description)

        comments = []
        log.warning("TikTok comments not available via opencli for %s", url)
        write_json(output_dir / "comments.json", comments)

        try:
            video_path = assets_dir / "video.mp4"
            subprocess.run(
                ["yt-dlp", "-o", str(video_path), url],
                capture_output=True,
                timeout=300,
            )
        except Exception as e:
            log.warning("yt-dlp download failed: %s", e)

        from datetime import datetime, timedelta, timezone

        refresh_state = {
            "current_interval_days": 14,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": 0,
        }

        meta = {
            "id": video_id,
            "platform": "tiktok",
            "url": url,
            "content_type": "video",
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "draft",
            "title": info.get("title", description[:80]),
            "author": info.get("author", info.get("nickname", "")),
            "published_at": info.get("createTime", ""),
            "language": "",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"description": "description.txt", "comments": "comments.json", "assets": []},
            "comments_refresh": refresh_state,
            "comment_history": [],
            "platform_meta": {
                "digg_count": info.get("digg_count", ""),
                "play_count": info.get("play_count", ""),
                "share_count": info.get("share_count", ""),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "video", output_dir, True)

    def fetch_comments(self, url: str) -> list[dict]:
        log.warning("TikTok comments not available via opencli")
        return []
