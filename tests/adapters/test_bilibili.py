import json


def test_bilibili_can_fetch():
    from data_factory.adapters.bilibili import BilibiliAdapter
    adapter = BilibiliAdapter()
    assert adapter.can_fetch("https://www.bilibili.com/video/BV1xxx")
    assert adapter.can_fetch("https://b23.tv/xxx")
    assert not adapter.can_fetch("https://youtube.com/watch?v=abc")


def test_bilibili_search(mocker):
    from data_factory.adapters.bilibili import BilibiliAdapter
    mocker.patch("data_factory.adapters.bilibili.run_opencli", return_value=[
        {"rank": 1, "title": "视频A", "url": "https://www.bilibili.com/video/BV1aaa", "author": "UP1"},
    ])
    adapter = BilibiliAdapter()
    urls = adapter.search("AI教程", limit=5)
    assert len(urls) == 1
    assert "BV1aaa" in urls[0]


def test_bilibili_fetch(mocker, tmp_path):
    from data_factory.adapters.bilibili import BilibiliAdapter
    video_data = [
        {"field": "Title", "value": "B站视频"},
        {"field": "Author", "value": "UP主"},
        {"field": "Description", "value": "视频描述"},
        {"field": "BVID", "value": "BV1test"},
    ]
    comments_data = [{"rank": 1, "author": "用户1", "text": "好评"}]

    def mock_opencli(platform, command, args=None, **kwargs):
        if command == "comments":
            return comments_data
        return video_data

    mocker.patch("data_factory.adapters.bilibili.run_opencli", side_effect=mock_opencli)
    mocker.patch("data_factory.adapters.bilibili.download_video", return_value=None)
    output_dir = tmp_path / "bilibili" / "BV1test"
    adapter = BilibiliAdapter()
    result = adapter.fetch("https://www.bilibili.com/video/BV1test", output_dir)

    assert result.status == "ok"
    assert result.content_type == "video"
    assert (output_dir / "meta.json").exists()
    assert (output_dir / "comments.json").exists()
    meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["platform"] == "bilibili"
    assert meta["id"] == "BV1test"
