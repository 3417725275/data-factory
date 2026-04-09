"""Bilibili adapter via opencli."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, maybe_write_text, maybe_write_json, now_iso
from data_factory.core.video import download_video

log = logging.getLogger(__name__)


def _extract_bvid(url: str) -> str:
    m = re.search(r"(BV[a-zA-Z0-9]+)", url)
    return m.group(1) if m else url.rstrip("/").split("/")[-1]


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

        info = self._get_video_info(bvid)

        description = info.get("description", info.get("title", ""))
        desc_file = maybe_write_text(output_dir / "description.txt", description)

        try:
            comments = self.fetch_comments(url)
        except Exception:
            comments = []
        comments_file = maybe_write_json(output_dir / "comments.json", comments)

        video_file = download_video(url, assets_dir)
        assets = []
        if video_file:
            rel = f"assets/{video_file.name}"
            assets.append(rel)

        subtitle_text = self._get_subtitle(bvid)
        transcript_file = maybe_write_text(output_dir / "transcript.txt", subtitle_text)

        from datetime import datetime, timedelta, timezone
        refresh_state = {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": len(comments),
        }

        files: dict = {"assets": assets}
        if desc_file:
            files["description"] = desc_file
        if comments_file:
            files["comments"] = comments_file
        if video_file:
            files["video"] = f"assets/{video_file.name}"
        if transcript_file:
            files["transcript"] = transcript_file

        meta = {
            "id": bvid,
            "platform": "bilibili",
            "url": url,
            "content_type": "video",
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "complete" if subtitle_text else "draft",
            "title": info.get("title", ""),
            "author": info.get("author", ""),
            "published_at": info.get("published", ""),
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": bool(subtitle_text),
            "images_downloaded": False,
            "files": files,
            "comments_refresh": refresh_state,
            "comment_history": [{"timestamp": now_iso(), "count": len(comments)}],
            "platform_meta": {
                "bvid": bvid,
                "score": info.get("score", ""),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "video", output_dir, not bool(subtitle_text))

    def _get_video_info(self, bvid: str) -> dict:
        """Get basic video info via search (bilibili has no dedicated video-info command)."""
        try:
            raw = run_opencli("bilibili", "search", [bvid, "--limit", "1"])
            if isinstance(raw, list) and raw:
                return raw[0] if isinstance(raw[0], dict) else {}
            return {}
        except Exception:
            return {}

    def _get_subtitle(self, bvid: str) -> str:
        """Try to get subtitle/transcript via opencli bilibili subtitle."""
        try:
            raw = run_opencli("bilibili", "subtitle", [bvid])
            if isinstance(raw, list):
                lines = [item.get("content", "") for item in raw if isinstance(item, dict)]
                return "\n".join(lines)
            return ""
        except Exception as e:
            log.info("No subtitle available for %s: %s", bvid, e)
            return ""

    def fetch_comments(self, url: str) -> list[dict]:
        bvid = _extract_bvid(url)
        return run_opencli("bilibili", "comments", [bvid])
