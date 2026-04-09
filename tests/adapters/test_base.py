import pytest
from pathlib import Path


def test_adapter_registry():
    from data_factory.adapters.base import ADAPTER_REGISTRY, PlatformAdapter
    from data_factory.core.schema import FetchResult

    class FakeAdapter(PlatformAdapter, adapter_name="fake_test"):
        URL_PATTERNS = ["fake.com"]

        def search(self, query, limit=20):
            return []

        def fetch(self, url, output_dir):
            return FetchResult("ok", "post", output_dir, False)

        def fetch_comments(self, url):
            return []

    assert "fake_test" in ADAPTER_REGISTRY
    assert ADAPTER_REGISTRY["fake_test"] is FakeAdapter


def test_can_fetch_matches_url_patterns():
    from data_factory.adapters.base import PlatformAdapter
    from data_factory.core.schema import FetchResult

    class UrlTestAdapter(PlatformAdapter, adapter_name="url_test"):
        URL_PATTERNS = ["example.com", "example.org"]

        def search(self, query, limit=20):
            return []

        def fetch(self, url, output_dir):
            return FetchResult("ok", "post", output_dir, False)

        def fetch_comments(self, url):
            return []

    adapter = UrlTestAdapter()
    assert adapter.can_fetch("https://example.com/page") is True
    assert adapter.can_fetch("https://example.org/page") is True
    assert adapter.can_fetch("https://other.com/page") is False


def test_import_file_raises_by_default():
    from data_factory.adapters.base import PlatformAdapter
    from data_factory.core.schema import FetchResult

    class NoImportAdapter(PlatformAdapter, adapter_name="no_import_test"):
        URL_PATTERNS = []

        def search(self, query, limit=20):
            return []

        def fetch(self, url, output_dir):
            return FetchResult("ok", "post", output_dir, False)

        def fetch_comments(self, url):
            return []

    adapter = NoImportAdapter()
    with pytest.raises(NotImplementedError):
        adapter.import_file(Path("/fake"), Path("/fake"))
