"""File I/O helpers for JSON and text."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def write_json(path: Path, data: dict | list, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def load_meta(output_dir: Path) -> dict | None:
    return load_json(output_dir / "meta.json")


def update_meta(output_dir: Path, updates: dict) -> None:
    """Merge *updates* into existing meta.json."""
    meta_path = output_dir / "meta.json"
    meta = load_json(meta_path) or {}
    meta.update(updates)
    write_json(meta_path, meta)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
