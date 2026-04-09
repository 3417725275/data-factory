"""YouTube adapter via opencli + yt-dlp."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, write_text, now_iso

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"


def _http_download(url: str, dest: Path) -> bool:
    import requests
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return True
    except Exception:
        return False


def _download_video_ytdlp(video_url: str, output_dir: Path) -> Path | None:
    """Download video (with audio) using yt-dlp."""
    if not shutil.which("yt-dlp"):
        log.warning("yt-dlp not installed, skipping video download")
        return None
    video_path = output_dir / "video.mp4"
    try:
        result = subprocess.run(
            ["yt-dlp",
             "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
             "--merge-output-format", "mp4",
             "-o", str(video_path),
             "--no-playlist", "--no-warnings", video_url],
            capture_output=True, text=True, timeout=600,
            encoding="utf-8", errors="replace", shell=_IS_WINDOWS,
        )
        if result.returncode == 0 and video_path.exists():
            log.info("Video downloaded: %s (%.1fMB)", video_path.name, video_path.stat().st_size / 1e6)
            return video_path
        actual = list(output_dir.glob("video.*"))
        return actual[0] if actual else None
    except Exception as e:
        log.warning("yt-dlp video download failed: %s", e)
        return None


def _extract_video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]+)", url)
    return m.group(1) if m else url.rstrip("/").split("/")[-1]


def _field_value_to_dict(rows: list[dict]) -> dict[str, str]:
    out = {}
    for row in rows:
        key = row.get("field", "").lower().replace(" ", "_")
        out[key] = row.get("value", "")
    return out


class YouTubeAdapter(PlatformAdapter, adapter_name="youtube"):
    URL_PATTERNS = ["youtube.com", "youtu.be"]

    def search(self, query: str, limit: int = 20) -> list[str]:
        results = run_opencli("youtube", "search", [query, "--limit", str(limit)])
        return [item["url"] for item in results if "url" in item]

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        video_id = _extract_video_id(url)

        try:
            raw_info = run_opencli("youtube", "video", [url])
        except Exception as e:
            return FetchResult("error", "video", output_dir, False, error=str(e))

        info = _field_value_to_dict(raw_info) if isinstance(raw_info, list) else raw_info

        description = info.get("description", "")
        write_text(output_dir / "description.txt", description)

        try:
            comments = self.fetch_comments(url)
        except Exception:
            comments = []
        write_json(output_dir / "comments.json", comments)

        assets = []
        thumb_url = info.get("thumbnail", "")
        if thumb_url:
            thumb_path = assets_dir / "thumbnail.jpg"
            if _http_download(thumb_url, thumb_path):
                assets.append("assets/thumbnail.jpg")

        video_file = _download_video_ytdlp(url, assets_dir)

        transcript_text = self._get_transcript(url)
        if transcript_text:
            write_text(output_dir / "transcript.txt", transcript_text)

        if video_file:
            assets.append(f"assets/{video_file.name}")

        files = {"description": "description.txt", "comments": "comments.json", "assets": assets}
        if video_file:
            files["video"] = f"assets/{video_file.name}"
        if transcript_text:
            files["transcript"] = "transcript.txt"

        from datetime import datetime, timedelta, timezone
        refresh_state = {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": len(comments),
        }

        meta = {
            "id": video_id,
            "platform": "youtube",
            "url": url,
            "content_type": "video",
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "complete" if transcript_text else "draft",
            "title": info.get("title", ""),
            "author": info.get("channel", ""),
            "published_at": info.get("publishdate", info.get("published", "")),
            "language": "",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": bool(transcript_text),
            "images_downloaded": bool(assets),
            "files": files,
            "comments_refresh": refresh_state,
            "comment_history": [{"timestamp": now_iso(), "count": len(comments)}],
            "platform_meta": {
                "channel": info.get("channel", ""),
                "channelid": info.get("channelid", ""),
                "duration": info.get("duration", ""),
                "views": info.get("views", ""),
                "likes": info.get("likes", ""),
                "category": info.get("category", ""),
                "comments_count": len(comments),
            },
        }
        write_json(output_dir / "meta.json", meta)

        return FetchResult("ok", "video", output_dir, not bool(transcript_text))

    def _get_transcript(self, url: str) -> str:
        """Try to get transcript via opencli youtube transcript."""
        try:
            raw = run_opencli("youtube", "transcript", [url])
            if isinstance(raw, list):
                lines = [item.get("text", "") for item in raw if isinstance(item, dict)]
                return "\n".join(lines)
            return ""
        except Exception as e:
            log.info("No transcript available: %s", e)
            return ""

    def fetch_comments(self, url: str) -> list[dict]:
        return run_opencli("youtube", "comments", [url])
