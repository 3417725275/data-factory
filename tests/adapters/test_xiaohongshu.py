import json


def test_xiaohongshu_can_fetch():
    from data_factory.adapters.xiaohongshu import XiaohongshuAdapter
    adapter = XiaohongshuAdapter()
    assert adapter.can_fetch("https://www.xiaohongshu.com/explore/abc123")
    assert adapter.can_fetch("https://xhslink.com/xxx")
    assert not adapter.can_fetch("https://youtube.com/watch?v=abc")


def test_xiaohongshu_search(mocker):
    from data_factory.adapters.xiaohongshu import XiaohongshuAdapter
    mocker.patch("data_factory.adapters.xiaohongshu.run_opencli", return_value=[
        {"title": "笔记A", "url": "https://www.xiaohongshu.com/explore/aaa111"},
    ])
    adapter = XiaohongshuAdapter()
    urls = adapter.search("穿搭", limit=5)
    assert len(urls) == 1


def test_xiaohongshu_fetch(mocker, tmp_path):
    from data_factory.adapters.xiaohongshu import XiaohongshuAdapter
    note_data = {"title": "我的笔记", "author": "小红书用户", "content": "笔记内容", "type": "post"}
    comments_data = [{"author": "评论者", "text": "好看"}]

    def mock_opencli(platform, command, args=None, **kwargs):
        if command == "comments":
            return comments_data
        if command == "download":
            return {}
        return note_data

    mocker.patch("data_factory.adapters.xiaohongshu.run_opencli", side_effect=mock_opencli)
    output_dir = tmp_path / "xiaohongshu" / "abc123"
    adapter = XiaohongshuAdapter()
    result = adapter.fetch("https://www.xiaohongshu.com/explore/abc123", output_dir)

    assert result.status == "ok"
    assert (output_dir / "meta.json").exists()
    meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["platform"] == "xiaohongshu"
    assert meta["id"] == "abc123"
