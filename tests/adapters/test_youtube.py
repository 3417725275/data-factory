import json
import pytest
from pathlib import Path


def test_youtube_can_fetch():
    from data_factory.adapters.youtube import YouTubeAdapter

    adapter = YouTubeAdapter()
    assert adapter.can_fetch("https://www.youtube.com/watch?v=abc123")
    assert adapter.can_fetch("https://youtu.be/abc123")
    assert not adapter.can_fetch("https://bilibili.com/video/BV1xxx")


def test_youtube_search(mocker):
    from data_factory.adapters.youtube import YouTubeAdapter

    mocker.patch("data_factory.adapters.youtube.run_opencli", return_value=[
        {"rank": 1, "title": "Video A", "url": "https://www.youtube.com/watch?v=aaa", "channel": "Ch1", "views": "1K", "duration": "10:00", "published": "1 day ago"},
        {"rank": 2, "title": "Video B", "url": "https://www.youtube.com/watch?v=bbb", "channel": "Ch2", "views": "2K", "duration": "5:00", "published": "2 days ago"},
    ])

    adapter = YouTubeAdapter()
    urls = adapter.search("LLM tutorial", limit=2)

    assert urls == [
        "https://www.youtube.com/watch?v=aaa",
        "https://www.youtube.com/watch?v=bbb",
    ]


def test_youtube_fetch_creates_folder(mocker, tmp_path):
    from data_factory.adapters.youtube import YouTubeAdapter

    video_data = [
        {"field": "Title", "value": "My Video"},
        {"field": "Channel", "value": "TestChannel"},
        {"field": "Published", "value": "2026-01-15"},
        {"field": "Views", "value": "123456"},
        {"field": "Likes", "value": "5000"},
        {"field": "Duration", "value": "5:25"},
        {"field": "Description", "value": "A test video description"},
        {"field": "Video ID", "value": "abc123"},
        {"field": "Thumbnail", "value": "https://img.youtube.com/vi/abc123/maxresdefault.jpg"},
    ]

    comments_data = [
        {"rank": 1, "author": "User1", "text": "Great video!", "likes": "10", "replies": "2", "time": "1 day ago"},
        {"rank": 2, "author": "User2", "text": "Thanks", "likes": "5", "replies": "0", "time": "2 days ago"},
    ]

    call_count = {"n": 0}

    def mock_opencli(platform, command, args=None, **kwargs):
        call_count["n"] += 1
        if command == "video":
            return video_data
        if command == "comments":
            return comments_data
        return []

    mocker.patch("data_factory.adapters.youtube.run_opencli", side_effect=mock_opencli)
    mocker.patch("data_factory.adapters.youtube._http_download", return_value=True)
    mocker.patch("data_factory.adapters.youtube._download_video_ytdlp", return_value=None)

    output_dir = tmp_path / "youtube" / "abc123"
    adapter = YouTubeAdapter()
    result = adapter.fetch("https://www.youtube.com/watch?v=abc123", output_dir)

    assert result.status == "ok"
    assert result.content_type == "video"
    assert result.needs_transcribe is True

    meta_path = output_dir / "meta.json"
    assert meta_path.exists()

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["id"] == "abc123"
    assert meta["platform"] == "youtube"
    assert meta["title"] == "My Video"
    assert meta["content_type"] == "video"
    assert meta["status"] == "draft"
    assert meta["content_fetched"] is True
    assert "platform_meta" in meta
    assert meta["platform_meta"]["views"] == "123456"

    assert (output_dir / "description.txt").exists()
    assert (output_dir / "comments.json").exists()


def test_youtube_fetch_comments(mocker):
    from data_factory.adapters.youtube import YouTubeAdapter

    mocker.patch("data_factory.adapters.youtube.run_opencli", return_value=[
        {"rank": 1, "author": "A", "text": "Hello", "likes": "1", "replies": "0", "time": "now"},
    ])

    adapter = YouTubeAdapter()
    comments = adapter.fetch_comments("https://www.youtube.com/watch?v=abc123")
    assert len(comments) == 1
    assert comments[0]["author"] == "A"
