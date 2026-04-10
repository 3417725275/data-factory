"""Xiaohongshu adapter via opencli."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, maybe_write_text, maybe_write_json, now_iso

log = logging.getLogger(__name__)


def _extract_note_id(url: str) -> str:
    m = re.search(r"(?:/explore/|/note/|/search_result/)([a-f0-9]+)", url)
    if m:
        return m.group(1)
    from urllib.parse import urlparse
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else url


def _normalize_url(url: str) -> str:
    """Convert search_result URL to explore URL for opencli compatibility."""
    from urllib.parse import urlparse, urlencode, parse_qs
    parsed = urlparse(url)
    m = re.search(r"/search_result/([a-f0-9]+)", parsed.path)
    if m:
        note_id = m.group(1)
        params = parse_qs(parsed.query)
        qs = {k: v[0] for k, v in params.items() if k in ("xsec_token", "xsec_source")}
        new_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        if qs:
            new_url += "?" + urlencode(qs)
        return new_url
    return url


def _field_value_to_dict(rows: list[dict]) -> dict[str, str]:
    """Convert [{field: k, value: v}, ...] to {k: v, ...}."""
    out = {}
    for row in rows:
        key = row.get("field", "").lower().replace(" ", "_")
        out[key] = row.get("value", "")
    return out


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

        normalized_url = _normalize_url(url)
        info = self._get_note_info(normalized_url, note_id)

        content = info.get("content", info.get("desc", ""))
        content_file = maybe_write_text(output_dir / "content.txt", content)

        try:
            comments = self.fetch_comments(normalized_url, note_id)
        except Exception:
            comments = []
        comments_file = maybe_write_json(output_dir / "comments.json", comments)

        downloaded_assets = self._download_media(normalized_url, note_id, assets_dir)

        content_type = info.get("type", "post")
        if content_type not in ("video", "post"):
            content_type = "post"
        if any(a.endswith((".mp4", ".mov")) for a in downloaded_assets):
            content_type = "video"
        needs_transcribe = content_type == "video"

        from datetime import datetime, timedelta, timezone
        refresh_state = {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": len(comments),
        }

        files: dict = {"assets": downloaded_assets}
        if content_file:
            files["content"] = content_file
        if comments_file:
            files["comments"] = comments_file

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
            "published_at": info.get("time", info.get("published_at", "")),
            "language": "zh",
            "content_fetched": bool(content_file),
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": bool(downloaded_assets),
            "files": files,
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

    def _get_note_info(self, url: str, note_id: str) -> dict:
        """Get note info. Try full URL first, then note_id only."""
        for identifier in [url, note_id]:
            try:
                raw = run_opencli("xiaohongshu", "note", [identifier])
            except Exception:
                continue

            if isinstance(raw, list) and raw:
                first = raw[0] if isinstance(raw[0], dict) else {}
                if "field" in first and "value" in first:
                    info = _field_value_to_dict(raw)
                else:
                    info = first
            elif isinstance(raw, dict):
                info = raw
            else:
                continue

            title = info.get("title", "")
            content = info.get("content", "")
            if title and title != "安全限制" and content != "访问链接异常":
                return info
            log.warning("xiaohongshu note returned restricted content with %s, trying fallback", identifier)

        log.warning("All attempts to get note info failed for %s", note_id)
        return {}

    def _download_media(self, url: str, note_id: str, assets_dir: Path) -> list[str]:
        """Download images/video. Try full URL first, then note_id."""
        media_exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".gif"}
        for identifier in [url, note_id]:
            try:
                result = run_opencli("xiaohongshu", "download",
                                     [identifier, "--output", str(assets_dir)],
                                     timeout=180)
                if isinstance(result, list):
                    failed = [r for r in result if isinstance(r, dict) and r.get("status") not in (None, "success")]
                    for r in failed:
                        log.warning("xiaohongshu download item failed for %s: %s", note_id, r)
            except Exception as e:
                log.warning("xiaohongshu download failed for %s (identifier=%s): %s", note_id, identifier, e)
                continue

            self._flatten_assets(assets_dir)
            files = [f for f in assets_dir.iterdir()
                     if f.is_file() and f.suffix.lower() in media_exts]
            if files:
                return [f"assets/{f.name}" for f in files]

        log.warning("All media download attempts failed for xiaohongshu note %s", note_id)
        return []

    @staticmethod
    def _flatten_assets(assets_dir: Path):
        """Move files from subdirectories up to assets_dir root, then remove empty subdirs."""
        import shutil
        for sub in [d for d in assets_dir.iterdir() if d.is_dir()]:
            for f in sub.rglob("*"):
                if f.is_file():
                    dest = assets_dir / f.name
                    if not dest.exists():
                        shutil.move(str(f), str(dest))
            shutil.rmtree(sub, ignore_errors=True)

    def fetch_comments(self, url: str, note_id: str | None = None) -> list[dict]:
        nid = note_id or _extract_note_id(url)
        for identifier in [url, nid]:
            try:
                result = run_opencli("xiaohongshu", "comments", [identifier])
                if isinstance(result, list) and result:
                    return result
            except Exception:
                continue
        return []

    def import_file(self, file_path: Path, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        import json
        data = json.loads(file_path.read_text(encoding="utf-8"))

        content = data.get("content", data.get("desc", ""))
        content_file = maybe_write_text(output_dir / "content.txt", content)
        comments_file = maybe_write_json(output_dir / "comments.json", data.get("comments", []))

        files: dict = {"assets": []}
        if content_file:
            files["content"] = content_file
        if comments_file:
            files["comments"] = comments_file

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
            "content_fetched": bool(content_file),
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": files,
            "comments_refresh": None,
            "comment_history": [],
            "platform_meta": data.get("platform_meta", {}),
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "post", output_dir, False)
