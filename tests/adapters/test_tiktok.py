import json
from pathlib import Path


def test_tiktok_can_fetch():
    from data_factory.adapters.tiktok import TikTokAdapter

    adapter = TikTokAdapter()
    assert adapter.can_fetch("https://www.tiktok.com/@user/video/123456")
    assert not adapter.can_fetch("https://youtube.com/watch?v=abc")


def test_tiktok_search(mocker):
    from data_factory.adapters.tiktok import TikTokAdapter

    mocker.patch(
        "data_factory.adapters.tiktok.run_opencli",
        return_value=[
            {"title": "TikTok A", "url": "https://www.tiktok.com/@user/video/111"},
        ],
    )
    adapter = TikTokAdapter()
    urls = adapter.search("dance", limit=5)
    assert len(urls) == 1


def test_tiktok_fetch(mocker, tmp_path):
    from data_factory.adapters.tiktok import TikTokAdapter

    video_data = [{"title": "My TikTok", "author": "user1", "desc": "Fun video", "digg_count": "1000"}]

    mocker.patch("data_factory.adapters.tiktok.run_opencli", return_value=video_data)
    mocker.patch("subprocess.run")

    output_dir = tmp_path / "tiktok" / "123456"
    adapter = TikTokAdapter()
    result = adapter.fetch("https://www.tiktok.com/@user/video/123456", output_dir)

    assert result.status == "ok"
    assert result.content_type == "video"
    assert result.needs_transcribe is True
    assert (output_dir / "meta.json").exists()
    meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["platform"] == "tiktok"


def test_tiktok_fetch_comments():
    from data_factory.adapters.tiktok import TikTokAdapter

    adapter = TikTokAdapter()
    comments = adapter.fetch_comments("https://www.tiktok.com/@user/video/123456")
    assert comments == []
