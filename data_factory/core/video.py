"""Shared yt-dlp video download with ffmpeg detection and fallback."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def download_video(url: str, output_dir: Path, filename: str = "video") -> Path | None:
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
        fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        extra = ["--merge-output-format", "mp4"]
    else:
        log.info("ffmpeg not found — using pre-merged format (quality may be lower)")
        fmt = "best[ext=mp4]/best"
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
            log.warning("yt-dlp exit %d: %s", result.returncode, result.stderr[:300])
        return None
    except subprocess.TimeoutExpired:
        log.warning("yt-dlp download timed out for %s", url)
        return None
    except Exception as e:
        log.warning("yt-dlp download failed: %s", e)
        return None
