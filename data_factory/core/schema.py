"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FetchResult:
    status: str  # "ok" | "error"
    content_type: str  # "video" | "post" | "topic" | "article" | "repo" | "issue"
    output_dir: Path
    needs_transcribe: bool
    audio_path: Path | None = None
    error: str | None = None


@dataclass
class CommentsRefreshState:
    current_interval_days: int
    consecutive_unchanged: int
    next_refresh_at: str  # ISO 8601
    last_refresh_at: str  # ISO 8601
    last_comment_count: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> CommentsRefreshState:
        return cls(
            current_interval_days=d["current_interval_days"],
            consecutive_unchanged=d["consecutive_unchanged"],
            next_refresh_at=d["next_refresh_at"],
            last_refresh_at=d["last_refresh_at"],
            last_comment_count=d["last_comment_count"],
        )
