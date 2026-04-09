"""Image download processor."""

from __future__ import annotations

import logging
from pathlib import Path

from data_factory.core.config import AppConfig
from data_factory.core.schema import FetchResult
from data_factory.core.storage import load_meta, update_meta
from data_factory.processors.base import Processor

log = logging.getLogger(__name__)


def download_file(url: str, dest: Path, timeout: int = 30) -> bool:
    import requests
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return True
    except Exception as e:
        log.warning("Failed to download %s: %s", url, e)
        return False


def _extract_image_urls(meta: dict) -> list[str]:
    urls = []
    pm = meta.get("platform_meta", {})
    for key, val in pm.items():
        if isinstance(val, str) and ("http" in val) and any(ext in val.lower() for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
            urls.append(val)
        if key.endswith("_url") and isinstance(val, str) and val.startswith("http"):
            if val not in urls:
                urls.append(val)
    return list(dict.fromkeys(urls))


class ImageDownloadProcessor(Processor, processor_name="images"):

    def should_run(self, result: FetchResult, output_dir: Path) -> bool:
        meta = load_meta(output_dir)
        if not meta:
            return False
        return not meta.get("images_downloaded", False)

    def process(self, result: FetchResult, output_dir: Path, config: AppConfig) -> None:
        meta = load_meta(output_dir) or {}
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)

        urls = _extract_image_urls(meta)
        downloaded = []
        timeout = config.network.timeout

        for i, url in enumerate(urls):
            ext = ".jpg"
            for candidate in [".png", ".gif", ".webp", ".jpeg"]:
                if candidate in url.lower():
                    ext = candidate
                    break
            local_path = assets_dir / f"img_{i}{ext}"
            if download_file(url, local_path, timeout=timeout):
                downloaded.append(str(local_path.relative_to(output_dir)))

        update_meta(output_dir, {"images_downloaded": True})
        log.info("Downloaded %d images for %s", len(downloaded), output_dir.name)
