"""Platform adapter abstract base class and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from data_factory.core.schema import FetchResult

ADAPTER_REGISTRY: dict[str, type["PlatformAdapter"]] = {}


class PlatformAdapter(ABC):
    URL_PATTERNS: list[str] = []

    def __init_subclass__(cls, *, adapter_name: str | None = None, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        if adapter_name is not None:
            ADAPTER_REGISTRY[adapter_name] = cls
            cls.adapter_name = adapter_name

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list[str]:
        """Search the platform and return a list of content URLs."""

    @abstractmethod
    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        """Fetch one item, write files into *output_dir*, return result."""

    @abstractmethod
    def fetch_comments(self, url: str) -> list[dict]:
        """Fetch all comments (paginated) for a content URL."""

    def can_fetch(self, url: str) -> bool:
        return any(pattern in url for pattern in self.URL_PATTERNS)

    def import_file(self, file_path: Path, output_dir: Path) -> FetchResult:
        raise NotImplementedError(
            f"{type(self).__name__} does not support file import"
        )
