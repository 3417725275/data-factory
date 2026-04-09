import pytest
from pathlib import Path
from data_factory.adapters.base import PlatformAdapter, ADAPTER_REGISTRY
from data_factory.core.schema import FetchResult


class _RouterTestAdapter(PlatformAdapter, adapter_name="_router_test"):
    URL_PATTERNS = ["routertest.com"]

    def search(self, query, limit=20):
        return []

    def fetch(self, url, output_dir):
        return FetchResult("ok", "post", output_dir, False)

    def fetch_comments(self, url):
        return []


def test_resolve_adapter_finds_match():
    from data_factory.core.router import resolve_adapter

    adapter = resolve_adapter("https://routertest.com/page/123")
    assert isinstance(adapter, _RouterTestAdapter)


def test_resolve_adapter_raises_for_unknown():
    from data_factory.core.router import resolve_adapter

    with pytest.raises(ValueError, match="No adapter found"):
        resolve_adapter("https://completely-unknown-site.xyz/page")
