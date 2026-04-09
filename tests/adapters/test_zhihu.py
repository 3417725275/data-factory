import json


def test_zhihu_can_fetch():
    from data_factory.adapters.zhihu import ZhihuAdapter
    adapter = ZhihuAdapter()
    assert adapter.can_fetch("https://www.zhihu.com/question/12345")
    assert adapter.can_fetch("https://zhuanlan.zhihu.com/p/67890")
    assert not adapter.can_fetch("https://youtube.com/watch?v=abc")


def test_zhihu_search(mocker):
    from data_factory.adapters.zhihu import ZhihuAdapter
    mocker.patch("data_factory.adapters.zhihu.run_opencli", return_value=[
        {"title": "问题A", "url": "https://www.zhihu.com/question/12345"},
    ])
    mocker.patch.object(ZhihuAdapter, "_cache_search_titles")
    adapter = ZhihuAdapter()
    urls = adapter.search("LLM", limit=5)
    assert len(urls) == 1


def test_zhihu_fetch(mocker, tmp_path):
    from data_factory.adapters.zhihu import ZhihuAdapter
    question_data = {"title": "如何学AI", "author": "知乎用户", "content": "答案内容", "voteup_count": "100"}

    mocker.patch("data_factory.adapters.zhihu.run_opencli", return_value=question_data)
    mocker.patch("data_factory.adapters.zhihu._fetch_title_via_cdp", return_value="如何学AI")
    output_dir = tmp_path / "zhihu" / "q_12345"
    adapter = ZhihuAdapter()
    result = adapter.fetch("https://www.zhihu.com/question/12345", output_dir)

    assert result.status == "ok"
    assert result.needs_transcribe is False
    assert (output_dir / "meta.json").exists()
    assert (output_dir / "content.md").exists()
    meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["platform"] == "zhihu"
    assert meta["content_type"] == "question"
    assert meta["title"] == "如何学AI"


def test_zhihu_fetch_comments():
    from data_factory.adapters.zhihu import ZhihuAdapter
    adapter = ZhihuAdapter()
    comments = adapter.fetch_comments("https://www.zhihu.com/question/12345")
    assert comments == []
