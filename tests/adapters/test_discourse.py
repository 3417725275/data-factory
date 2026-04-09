import json
from pathlib import Path


def test_discourse_can_fetch():
    from data_factory.adapters.discourse import DiscourseAdapter

    adapter = DiscourseAdapter(base_url="https://forum.example.com")
    assert adapter.can_fetch("https://forum.example.com/t/my-topic/123")
    assert not adapter.can_fetch("https://other.com/page")


def test_discourse_search(mocker):
    from data_factory.adapters.discourse import DiscourseAdapter

    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = {"topics": [{"slug": "my-topic", "id": 123}]}
    mocker.patch("data_factory.adapters.discourse.requests.get", return_value=mock_resp)

    adapter = DiscourseAdapter(base_url="https://forum.example.com")
    urls = adapter.search("test query", limit=5)
    assert len(urls) == 1
    assert "123" in urls[0]


def test_discourse_fetch(mocker, tmp_path):
    from data_factory.adapters.discourse import DiscourseAdapter

    topic_data = {
        "title": "My Topic",
        "category_id": 5,
        "views": 100,
        "reply_count": 2,
        "like_count": 10,
        "post_stream": {
            "posts": [
                {"username": "author1", "cooked": "<p>First post content</p>", "created_at": "2026-01-01"},
                {"username": "replier1", "cooked": "<p>Reply 1</p>"},
                {"username": "replier2", "cooked": "<p>Reply 2</p>"},
            ]
        },
    }
    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = topic_data
    mocker.patch("data_factory.adapters.discourse.requests.get", return_value=mock_resp)

    output_dir = tmp_path / "discourse" / "123"
    adapter = DiscourseAdapter(base_url="https://forum.example.com")
    result = adapter.fetch("https://forum.example.com/t/my-topic/123", output_dir)

    assert result.status == "ok"
    assert result.content_type == "topic"
    assert (output_dir / "meta.json").exists()
    assert (output_dir / "content.html").exists()
    assert (output_dir / "posts.json").exists()
    meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["title"] == "My Topic"
    assert meta["id"] == "123"
