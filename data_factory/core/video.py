"""Shared yt-dlp video download with ffmpeg detection and fallback."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"

_QUALITY_FORMAT_MAP = {
    "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]",
    "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
    "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
    "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
}

_QUALITY_FORMAT_NO_FFMPEG = {
    "480p": "best[height<=480][ext=mp4]/best[height<=480]",
    "720p": "best[height<=720][ext=mp4]/best[height<=720]",
    "1080p": "best[height<=1080][ext=mp4]/best[height<=1080]",
    "best": "best[ext=mp4]/best",
}


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _log_detailed_failure(url: str, stderr: str) -> None:
    """Classify yt-dlp failure and log a specific, actionable message."""
    s = stderr.lower() if stderr else ""
    if "no video formats found" in s:
        log.warning(
            "yt-dlp: No video formats found for %s — "
            "this usually means the platform requires login/cookies. "
            "Bilibili should use 'opencli bilibili download' instead of yt-dlp.",
            url,
        )
    elif "sign in to confirm" in s or "age" in s:
        log.warning(
            "yt-dlp: Age/login restriction for %s — "
            "video requires authentication to download.",
            url,
        )
    elif "private video" in s:
        log.warning("yt-dlp: Video is private: %s", url)
    elif "copyright" in s or "blocked" in s:
        log.warning("yt-dlp: Video blocked (copyright/region): %s", url)
    elif "http error 403" in s or "403" in s:
        log.warning("yt-dlp: HTTP 403 Forbidden for %s — possible geo-restriction or anti-bot", url)
    else:
        log.warning("yt-dlp failed for %s: %s", url, stderr[:300] if stderr else "unknown error")


def download_video(
    url: str,
    output_dir: Path,
    filename: str = "video",
    quality: str = "720p",
) -> Path | None:
    """Download video via yt-dlp with automatic ffmpeg fallback.

    When ffmpeg is available, downloads best video+audio streams and merges them.
    When ffmpeg is missing, downloads a pre-merged format (lower quality but single file).
    Returns the path to the downloaded file, or None on failure.
    """
    if not shutil.which("yt-dlp"):
        log.warning("yt-dlp not installed, skipping video download")
        return None

    out_path = output_dir / f"{filename}.mp4"

    if _has_ffmpeg():
        fmt = _QUALITY_FORMAT_MAP.get(quality, _QUALITY_FORMAT_MAP["720p"])
        extra = ["--merge-output-format", "mp4"]
    else:
        log.info("ffmpeg not found — using pre-merged format (quality may be lower)")
        fmt = _QUALITY_FORMAT_NO_FFMPEG.get(quality, _QUALITY_FORMAT_NO_FFMPEG["720p"])
        extra = []

    cmd = ["yt-dlp", "-f", fmt, *extra,
           "-o", str(out_path), "--no-playlist", "--no-warnings", url]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            encoding="utf-8", errors="replace", shell=_IS_WINDOWS,
        )
        if result.returncode == 0 and out_path.exists():
            log.info("Video downloaded: %s (%.1fMB)", out_path.name, out_path.stat().st_size / 1e6)
            return out_path

        candidates = sorted(output_dir.glob(f"{filename}.*"),
                            key=lambda p: p.stat().st_size, reverse=True)
        if candidates:
            best = candidates[0]
            if best.suffix != ".mp4":
                renamed = best.with_suffix(".mp4")
                best.rename(renamed)
                best = renamed
            return best

        if result.returncode != 0:
            _log_detailed_failure(url, result.stderr)
        return None
    except subprocess.TimeoutExpired:
        log.warning("yt-dlp download timed out for %s", url)
        return None
    except Exception as e:
        log.warning("yt-dlp download failed: %s", e)
        return None
