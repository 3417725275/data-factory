"""Incremental index manager."""

from __future__ import annotations

from pathlib import Path

from data_factory.core.storage import load_json, write_json, now_iso


class Indexer:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def upsert_item(self, platform: str, item_id: str, meta: dict) -> None:
        platform_dir = self.output_dir / platform
        platform_dir.mkdir(parents=True, exist_ok=True)
        index_path = platform_dir / "index.json"

        index = load_json(index_path) or {
            "platform": platform,
            "updated_at": None,
            "count": 0,
            "items": {},
        }

        refresh = meta.get("comments_refresh", {})
        index["items"][item_id] = {
            "title": meta.get("title", ""),
            "url": meta.get("url", ""),
            "content_type": meta.get("content_type", ""),
            "status": meta.get("status", ""),
            "fetched_at": meta.get("fetched_at", ""),
            "published_at": meta.get("published_at"),
            "last_comment_refresh": refresh.get("last_refresh_at"),
            "comment_count": refresh.get("last_comment_count", 0),
            "path": f"{item_id}/",
        }
        index["count"] = len(index["items"])
        index["updated_at"] = now_iso()

        write_json(index_path, index)
        self._update_global_index(platform, index["count"])

    def remove_item(self, platform: str, item_id: str) -> None:
        index_path = self.output_dir / platform / "index.json"
        index = load_json(index_path)
        if not index:
            return
        index["items"].pop(item_id, None)
        index["count"] = len(index["items"])
        index["updated_at"] = now_iso()
        write_json(index_path, index)
        self._update_global_index(platform, index["count"])

    def rebuild(self, platform: str | None = None) -> None:
        platforms = [platform] if platform else self._list_platforms()
        for p in platforms:
            platform_dir = self.output_dir / p
            if not platform_dir.is_dir():
                continue
            items: dict[str, dict] = {}
            for item_dir in sorted(platform_dir.iterdir()):
                if not item_dir.is_dir():
                    continue
                meta_path = item_dir / "meta.json"
                meta = load_json(meta_path)
                if not meta:
                    continue
                item_id = meta.get("id", item_dir.name)
                refresh = meta.get("comments_refresh", {})
                items[item_id] = {
                    "title": meta.get("title", ""),
                    "url": meta.get("url", ""),
                    "content_type": meta.get("content_type", ""),
                    "status": meta.get("status", ""),
                    "fetched_at": meta.get("fetched_at", ""),
                    "published_at": meta.get("published_at"),
                    "last_comment_refresh": refresh.get("last_refresh_at"),
                    "comment_count": refresh.get("last_comment_count", 0),
                    "path": f"{item_id}/",
                }
            write_json(platform_dir / "index.json", {
                "platform": p,
                "updated_at": now_iso(),
                "count": len(items),
                "items": items,
            })
            self._update_global_index(p, len(items))

    def _update_global_index(self, platform: str, count: int) -> None:
        global_path = self.output_dir / "global_index.json"
        gi = load_json(global_path) or {
            "updated_at": None,
            "platforms": {},
            "total_count": 0,
        }
        gi["platforms"][platform] = {
            "count": count,
            "last_updated": now_iso(),
        }
        gi["total_count"] = sum(p["count"] for p in gi["platforms"].values())
        gi["updated_at"] = now_iso()
        write_json(global_path, gi)

    def _list_platforms(self) -> list[str]:
        return [
            d.name
            for d in self.output_dir.iterdir()
            if d.is_dir() and (d / "index.json").exists()
        ]
