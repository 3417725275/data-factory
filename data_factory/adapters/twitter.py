"""Twitter/X adapter via opencli."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import requests

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, maybe_write_text, maybe_write_json, now_iso

log = logging.getLogger(__name__)

_MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov"}


def _extract_tweet_id(url: str) -> str:
    m = re.search(r"status/(\d+)", url)
    return m.group(1) if m else url.rstrip("/").split("/")[-1]


def _flatten_assets(assets_dir: Path):
    """Move files from subdirectories up to assets_dir root, then remove empty subdirs."""
    import shutil
    if not assets_dir.exists():
        return
    for sub in [d for d in assets_dir.iterdir() if d.is_dir()]:
        for f in sub.rglob("*"):
            if f.is_file():
                dest = assets_dir / f.name
                if not dest.exists():
                    shutil.move(str(f), str(dest))
        shutil.rmtree(sub, ignore_errors=True)


_MEDIA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://x.com/",
}


def _download_media_urls(urls: list[str], assets_dir: Path) -> list[str]:
    """Download a list of image/video URLs into assets_dir. Returns relative paths."""
    downloaded = []
    for i, url in enumerate(urls):
        try:
            resp = requests.get(url, timeout=30, headers=_MEDIA_HEADERS)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if "jpeg" in ct or "jpg" in ct:
                ext = ".jpg"
            elif "png" in ct:
                ext = ".png"
            elif "webp" in ct:
                ext = ".webp"
            elif "gif" in ct:
                ext = ".gif"
            elif "mp4" in ct or "video" in ct:
                ext = ".mp4"
            else:
                ext = ".jpg"
            dest = assets_dir / f"media_{i + 1}{ext}"
            dest.write_bytes(resp.content)
            downloaded.append(f"assets/{dest.name}")
        except requests.HTTPError as e:
            log.warning("HTTP %d downloading media %s: %s", e.response.status_code if e.response else 0, url, e)
        except Exception as e:
            log.warning("Failed to download media %s: %s", url, e)
    return downloaded


def _extract_media_urls(tweet_data: dict) -> list[str]:
    """Extract image/video URLs from tweet data returned by opencli."""
    urls = []
    for key in ("media", "photos", "images", "videos"):
        val = tweet_data.get(key, [])
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    urls.append(item)
                elif isinstance(item, dict):
                    urls.append(item.get("url", item.get("media_url_https", "")))
        elif isinstance(val, str) and val:
            urls.append(val)

    photo_url = tweet_data.get("photo", tweet_data.get("image", ""))
    if photo_url:
        urls.append(photo_url)

    return [u for u in urls if u and u.startswith("http")]


def _fetch_media_via_syndication(tweet_id: str) -> list[str]:
    """Fetch media URLs from Twitter's public Syndication API (no auth required).

    This is the primary fallback when opencli twitter download returns "No media found".
    """
    try:
        resp = requests.get(
            f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=x",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception as e:
        log.debug("Syndication API request failed: %s", e)
        return []

    urls = []
    for detail in data.get("mediaDetails", []):
        media_url = detail.get("media_url_https", "")
        if media_url:
            if detail.get("type") == "photo":
                urls.append(f"{media_url}?name=large")
            elif detail.get("type") == "video":
                variants = detail.get("video_info", {}).get("variants", [])
                best = max(
                    (v for v in variants if v.get("content_type") == "video/mp4"),
                    key=lambda v: v.get("bitrate", 0),
                    default=None,
                )
                if best:
                    urls.append(best["url"])
            else:
                urls.append(media_url)

    return urls


class TwitterAdapter(PlatformAdapter, adapter_name="twitter"):
    URL_PATTERNS = ["twitter.com", "x.com"]

    def search(self, query: str, limit: int = 20) -> list[str]:
        results = run_opencli("twitter", "search", [query, "--limit", str(limit)])
        return [item["url"] for item in results if "url" in item]

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        tweet_id = _extract_tweet_id(url)

        try:
            raw = run_opencli("twitter", "thread", [tweet_id])
        except Exception as e:
            return FetchResult("error", "post", output_dir, False, error=str(e))

        if isinstance(raw, list) and raw:
            main_tweet = raw[0] if isinstance(raw[0], dict) else {}
            replies = raw[1:] if len(raw) > 1 else []
        elif isinstance(raw, dict):
            main_tweet = raw
            replies = raw.get("replies", [])
        else:
            main_tweet = {}
            replies = []

        content = main_tweet.get("text", main_tweet.get("content", ""))
        content_file = maybe_write_text(output_dir / "content.txt", content)
        comments_file = maybe_write_json(output_dir / "comments.json", replies)

        assets = []
        try:
            run_opencli("twitter", "download",
                        ["--tweet-url", url, "--output", str(assets_dir)],
                        timeout=120)
            _flatten_assets(assets_dir)
            assets = [f"assets/{f.name}" for f in assets_dir.iterdir()
                      if f.is_file() and f.suffix.lower() in _MEDIA_EXTS]
        except Exception as e:
            log.warning("opencli twitter download failed: %s", e)

        if not assets:
            media_urls = _extract_media_urls(main_tweet)
            if not media_urls:
                media_urls = _fetch_media_via_syndication(tweet_id)
            if media_urls:
                assets = _download_media_urls(media_urls, assets_dir)

        from datetime import datetime, timedelta, timezone

        refresh_state = {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": len(replies),
        }

        files: dict = {"assets": assets}
        if content_file:
            files["content"] = content_file
        if comments_file:
            files["comments"] = comments_file

        meta = {
            "id": tweet_id,
            "platform": "twitter",
            "url": url,
            "content_type": "post",
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": content[:80] if content else "",
            "author": main_tweet.get("author", main_tweet.get("username", "")),
            "published_at": main_tweet.get("time", ""),
            "language": "",
            "content_fetched": bool(content),
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": bool(assets),
            "files": files,
            "comments_refresh": refresh_state,
            "comment_history": [{"timestamp": now_iso(), "count": len(replies)}],
            "platform_meta": {
                "likes": main_tweet.get("likes", ""),
                "retweets": main_tweet.get("retweets", ""),
                "replies_count": len(replies),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "post", output_dir, False)

    def fetch_comments(self, url: str) -> list[dict]:
        tweet_id = _extract_tweet_id(url)
        raw = run_opencli("twitter", "thread", [tweet_id])
        if isinstance(raw, list) and len(raw) > 1:
            return raw[1:]
        if isinstance(raw, dict):
            return raw.get("replies", [])
        return []
