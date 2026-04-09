import json


def test_reddit_can_fetch():
    from data_factory.adapters.reddit import RedditAdapter
    adapter = RedditAdapter()
    assert adapter.can_fetch("https://www.reddit.com/r/Python/comments/abc123/test")
    assert not adapter.can_fetch("https://youtube.com/watch?v=abc")


def test_reddit_search(mocker):
    from data_factory.adapters.reddit import RedditAdapter
    mocker.patch("data_factory.adapters.reddit.run_opencli", return_value=[
        {"rank": 1, "title": "Post A", "url": "https://reddit.com/r/test/comments/abc/post_a"},
    ])
    adapter = RedditAdapter()
    urls = adapter.search("python tips", limit=5)
    assert len(urls) == 1


def test_reddit_fetch(mocker, tmp_path):
    from data_factory.adapters.reddit import RedditAdapter
    post_data = [
        {"title": "My Post", "author": "user1", "body": "Post content here", "score": "100"},
        {"author": "commenter1", "body": "Great post!", "score": "10"},
        {"author": "commenter2", "body": "Thanks", "score": "5"},
    ]
    mocker.patch("data_factory.adapters.reddit.run_opencli", return_value=post_data)

    output_dir = tmp_path / "reddit" / "t3_abc"
    adapter = RedditAdapter()
    result = adapter.fetch("https://www.reddit.com/r/Python/comments/abc/test", output_dir)

    assert result.status == "ok"
    assert result.content_type == "post"
    assert result.needs_transcribe is False
    assert (output_dir / "meta.json").exists()
    assert (output_dir / "content.md").exists()
    assert (output_dir / "comments.json").exists()
    meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["platform"] == "reddit"
