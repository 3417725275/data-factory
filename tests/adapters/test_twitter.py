import json
from pathlib import Path


def test_twitter_can_fetch():
    from data_factory.adapters.twitter import TwitterAdapter

    adapter = TwitterAdapter()
    assert adapter.can_fetch("https://twitter.com/user/status/123456")
    assert adapter.can_fetch("https://x.com/user/status/789")
    assert not adapter.can_fetch("https://youtube.com/watch?v=abc")


def test_twitter_search(mocker):
    from data_factory.adapters.twitter import TwitterAdapter

    mocker.patch(
        "data_factory.adapters.twitter.run_opencli",
        return_value=[
            {"title": "Tweet A", "url": "https://twitter.com/user/status/111"},
        ],
    )
    adapter = TwitterAdapter()
    urls = adapter.search("AI news", limit=5)
    assert len(urls) == 1


def test_twitter_fetch(mocker, tmp_path):
    from data_factory.adapters.twitter import TwitterAdapter

    thread_data = [
        {"text": "Main tweet content", "author": "user1", "likes": "100", "retweets": "50"},
        {"text": "Reply 1", "author": "user2"},
    ]

    def mock_opencli(platform, command, args=None, **kwargs):
        if command == "download":
            return {}
        return thread_data

    mocker.patch("data_factory.adapters.twitter.run_opencli", side_effect=mock_opencli)
    output_dir = tmp_path / "twitter" / "123456"
    adapter = TwitterAdapter()
    result = adapter.fetch("https://twitter.com/user/status/123456", output_dir)

    assert result.status == "ok"
    assert result.content_type == "post"
    assert (output_dir / "meta.json").exists()
    assert (output_dir / "content.txt").exists()
    meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["platform"] == "twitter"
    assert meta["id"] == "123456"
