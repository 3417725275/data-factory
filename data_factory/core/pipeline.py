"""Staged pipeline orchestrator: fetch -> process -> index."""

from __future__ import annotations

import logging
from pathlib import Path

from data_factory.adapters.base import ADAPTER_REGISTRY, PlatformAdapter
from data_factory.core.config import AppConfig
from data_factory.core.indexer import Indexer
from data_factory.core.refresh import compute_next_refresh, needs_comment_refresh
from data_factory.core.schema import CommentsRefreshState, FetchResult
from data_factory.core.storage import load_json, load_meta, update_meta, write_json, now_iso

log = logging.getLogger(__name__)


def get_adapter(platform: str, config: AppConfig) -> PlatformAdapter:
    cls = ADAPTER_REGISTRY.get(platform)
    if cls is None:
        raise ValueError(f"Unknown platform: {platform}")
    return cls()


class Pipeline:
    def __init__(self, config: AppConfig):
        self.config = config
        self.indexer = Indexer(config.output_dir)

    def resolve_output_dir(self, platform: str, item_id: str) -> Path:
        return self.config.output_dir / platform / item_id

    def run_full(self, url: str, platform: str) -> FetchResult | None:
        adapter = get_adapter(platform, self.config)
        item_id = self._extract_id(url, platform)
        output_dir = self.resolve_output_dir(platform, item_id)

        meta = load_meta(output_dir)
        if meta and meta.get("content_fetched"):
            log.info("Content already fetched, checking comments: %s", url)
            self.run_refresh(url, platform)
            return None

        result = adapter.fetch(url, output_dir)
        if result.status == "error":
            log.error("Fetch failed for %s: %s", url, result.error)
            return result

        meta = load_meta(output_dir)
        if meta:
            self.indexer.upsert_item(platform, meta.get("id", item_id), meta)

        return result

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

        from data_factory.processors.base import PROCESSOR_REGISTRY
        proc_cls = PROCESSOR_REGISTRY.get(step)
        if proc_cls is None:
            log.error("Unknown processor step: %s", step)
            return

        proc = proc_cls()
        if proc.should_run(result, output_dir):
            proc.process(result, output_dir, self.config)

    def _extract_id(self, url: str, platform: str) -> str:
        import re
        if platform == "youtube":
            m = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]+)", url)
            if m:
                return m.group(1)
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else url
