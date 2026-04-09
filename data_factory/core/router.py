"""URL to adapter routing."""

from __future__ import annotations

from data_factory.adapters.base import ADAPTER_REGISTRY, PlatformAdapter


def resolve_adapter(url: str) -> PlatformAdapter:
    """Find and instantiate the adapter whose URL_PATTERNS match *url*."""
    for name, cls in ADAPTER_REGISTRY.items():
        instance = cls()
        if instance.can_fetch(url):
            return instance
    raise ValueError(f"No adapter found for URL: {url}")
