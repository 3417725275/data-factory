"""Staged pipeline orchestrator: fetch -> process -> index."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from data_factory.adapters.base import ADAPTER_REGISTRY, PlatformAdapter
from data_factory.core.config import AppConfig
from data_factory.core.indexer import Indexer
from data_factory.core.refresh import compute_next_refresh, needs_comment_refresh
from data_factory.core.schema import CommentsRefreshState, FetchResult
from data_factory.core.storage import load_json, load_meta, update_meta, write_json, now_iso

log = logging.getLogger(__name__)

_DISCOURSE_ALIASES = {
    "discourse_cn", "discourse_en", "discourse_zh", "discourse_intl",
}


def get_adapter(platform: str, config: AppConfig) -> PlatformAdapter:
    """Instantiate a platform adapter, injecting config where needed."""
    pcfg = config.platforms.get(platform)

    cls = ADAPTER_REGISTRY.get(platform)

    if cls is None and platform in _DISCOURSE_ALIASES or (cls is None and platform.startswith("discourse")):
        cls = ADAPTER_REGISTRY.get("discourse")

    if cls is None:
        raise ValueError(f"Unknown platform: {platform}")

    if platform.startswith("discourse") and platform != "discourse":
        base_url = pcfg.base_url if pcfg else ""
        return cls(base_url=base_url or "", platform_key=platform)

    if hasattr(cls, "__init__"):
        import inspect
        sig = inspect.signature(cls.__init__)
        params = set(sig.parameters.keys()) - {"self"}

        kwargs = {}
        if "base_url" in params and pcfg:
            kwargs["base_url"] = pcfg.base_url or ""
        if "platform_key" in params:
            kwargs["platform_key"] = platform
        if "token" in params and pcfg:
            kwargs["token"] = pcfg.token
        if kwargs:
            return cls(**kwargs)

    return cls()


class Pipeline:
    def __init__(self, config: AppConfig):
        self.config = config
        self.indexer = Indexer(config.output_dir)

    def resolve_output_dir(self, platform: str, item_id: str) -> Path:
        return self.config.output_dir / platform / item_id

    def _rate_limit(self, platform: str) -> None:
        pcfg = self.config.platforms.get(platform)
        if pcfg and pcfg.rate_limit > 0:
            time.sleep(pcfg.rate_limit)

    def run_full(self, url: str, platform: str, force: bool = False) -> FetchResult | None:
        adapter = get_adapter(platform, self.config)
        item_id = self._extract_id(url, platform)
        output_dir = self.resolve_output_dir(platform, item_id)

        meta = load_meta(output_dir)
        if meta and meta.get("content_fetched") and not force:
            log.info("Content already fetched, checking comments: %s", url)
            self.run_refresh(url, platform)
            return None

        self._rate_limit(platform)
        result = adapter.fetch(url, output_dir)
        if result.status == "error":
            log.error("Fetch failed for %s: %s", url, result.error)
            return result

        self._run_processors(result, output_dir)

        meta = load_meta(output_dir)
        if meta:
            self.indexer.upsert_item(platform, meta.get("id", item_id), meta)

        return result

    def _run_processors(self, result: FetchResult, output_dir: Path) -> None:
        """Auto-run applicable processors after fetch."""
        import data_factory.processors  # noqa: F401
        from data_factory.processors.base import PROCESSOR_REGISTRY

        for name, proc_cls in PROCESSOR_REGISTRY.items():
            proc = proc_cls()
            try:
                if proc.should_run(result, output_dir):
                    log.info("Running processor: %s on %s", name, output_dir.name)
                    proc.process(result, output_dir, self.config)
            except Exception as e:
                log.error("Processor %s failed for %s: %s", name, output_dir.name, e)

    def run_refresh(self, url: str, platform: str) -> None:
        adapter = get_adapter(platform, self.config)
        item_id = self._extract_id(url, platform)
        output_dir = self.resolve_output_dir(platform, item_id)

        meta = load_meta(output_dir)
        if not meta:
            log.warning("No meta.json found for %s, skipping refresh", url)
            return

        if not needs_comment_refresh(meta):
            log.info("Comment refresh not due for %s", url)
            return

        self._rate_limit(platform)
        try:
            comments = adapter.fetch_comments(url)
        except Exception as e:
            log.error("Failed to fetch comments for %s: %s", url, e)
            return

        write_json(output_dir / "comments.json", comments)

        refresh_raw = meta.get("comments_refresh", {})
        old_state = CommentsRefreshState(
            current_interval_days=refresh_raw.get("current_interval_days", 1),
            consecutive_unchanged=refresh_raw.get("consecutive_unchanged", 0),
            next_refresh_at=refresh_raw.get("next_refresh_at", ""),
            last_refresh_at=refresh_raw.get("last_refresh_at", ""),
            last_comment_count=refresh_raw.get("last_comment_count", 0),
        )

        new_state = compute_next_refresh(len(comments), old_state)

        history = meta.get("comment_history", [])
        history.append({"timestamp": now_iso(), "count": len(comments)})

        update_meta(output_dir, {
            "comments_refresh": new_state.to_dict(),
            "comment_history": history,
        })

        meta = load_meta(output_dir)
        if meta:
            self.indexer.upsert_item(platform, meta.get("id", item_id), meta)

    def run_step(self, step: str, platform: str, item_id: str) -> None:
        output_dir = self.resolve_output_dir(platform, item_id)
        meta = load_meta(output_dir)
        if not meta:
            log.error("No meta.json found for %s/%s", platform, item_id)
            return

        content_type = meta.get("content_type", "")
        result = FetchResult(
            status="ok",
            content_type=content_type,
            output_dir=output_dir,
            needs_transcribe=(content_type == "video"),
        )

        import data_factory.processors  # noqa: F401
        from data_factory.processors.base import PROCESSOR_REGISTRY
        proc_cls = PROCESSOR_REGISTRY.get(step)
        if proc_cls is None:
            log.error("Unknown processor step: %s", step)
            return

        proc = proc_cls()
        if proc.should_run(result, output_dir):
            proc.process(result, output_dir, self.config)

    def _extract_id(self, url: str, platform: str) -> str:
        """Best-effort ID extraction from URL."""
        import re
        if platform == "youtube":
            m = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]+)", url)
            if m:
                return m.group(1)
        if platform == "bilibili":
            m = re.search(r"(BV[a-zA-Z0-9]+)", url)
            if m:
                return m.group(1)
        if platform == "reddit":
            m = re.search(r"/comments/([a-z0-9]+)", url)
            if m:
                return f"t3_{m.group(1)}"
        if platform in ("xiaohongshu",):
            m = re.search(r"(?:/explore/|note/)([a-f0-9]+)", url)
            if m:
                return m.group(1)
        if platform == "zhihu":
            m = re.search(r"question/(\d+)", url)
            if m:
                return f"q_{m.group(1)}"
        if platform in ("twitter",):
            m = re.search(r"status/(\d+)", url)
            if m:
                return m.group(1)
        if platform == "tiktok":
            m = re.search(r"video/(\d+)", url)
            if m:
                return m.group(1)
        if platform == "github":
            m = re.match(r"https?://github\.com/([^/]+)/([^/]+)(?:/issues/(\d+))?", url)
            if m:
                if m.group(3):
                    return f"{m.group(1)}_{m.group(2)}_issue_{m.group(3)}"
                return f"{m.group(1)}_{m.group(2)}"
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else url
