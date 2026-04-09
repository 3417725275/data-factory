import json
from pathlib import Path


def test_upsert_item_creates_new_index(tmp_output):
    from data_factory.core.indexer import Indexer

    indexer = Indexer(tmp_output)
    meta = {
        "id": "abc123",
        "title": "Test Video",
        "url": "https://youtube.com/watch?v=abc123",
        "content_type": "video",
        "status": "complete",
        "fetched_at": "2026-04-08T15:00:00Z",
        "published_at": "2026-01-15T10:00:00Z",
        "comments_refresh": {
            "last_refresh_at": "2026-04-08T15:00:00Z",
            "last_comment_count": 50,
        },
    }

    indexer.upsert_item("youtube", "abc123", meta)

    index_path = tmp_output / "youtube" / "index.json"
    assert index_path.exists()

    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    assert index["platform"] == "youtube"
    assert index["count"] == 1
    assert "abc123" in index["items"]
    assert index["items"]["abc123"]["title"] == "Test Video"


def test_upsert_item_updates_existing(tmp_output):
    from data_factory.core.indexer import Indexer

    indexer = Indexer(tmp_output)
    meta1 = {
        "id": "abc", "title": "V1", "url": "u", "content_type": "video",
        "status": "draft", "fetched_at": "2026-04-08T15:00:00Z",
    }
    meta2 = {
        "id": "abc", "title": "V1 Updated", "url": "u", "content_type": "video",
        "status": "complete", "fetched_at": "2026-04-08T15:00:00Z",
        "comments_refresh": {"last_refresh_at": "2026-04-09T00:00:00Z", "last_comment_count": 10},
    }

    indexer.upsert_item("youtube", "abc", meta1)
    indexer.upsert_item("youtube", "abc", meta2)

    from data_factory.core.storage import load_json
    index = load_json(tmp_output / "youtube" / "index.json")
    assert index["count"] == 1
    assert index["items"]["abc"]["status"] == "complete"
    assert index["items"]["abc"]["title"] == "V1 Updated"


def test_upsert_item_updates_global_index(tmp_output):
    from data_factory.core.indexer import Indexer
    from data_factory.core.storage import load_json

    indexer = Indexer(tmp_output)
    meta = {
        "id": "a", "title": "T", "url": "u", "content_type": "post",
        "status": "complete", "fetched_at": "2026-04-08T15:00:00Z",
    }

    indexer.upsert_item("reddit", "a", meta)

    gi = load_json(tmp_output / "global_index.json")
    assert gi["total_count"] == 1
    assert gi["platforms"]["reddit"]["count"] == 1


def test_rebuild_scans_folders(tmp_output):
    from data_factory.core.indexer import Indexer
    from data_factory.core.storage import write_json

    yt_dir = tmp_output / "youtube" / "vid1"
    yt_dir.mkdir(parents=True)
    write_json(yt_dir / "meta.json", {
        "id": "vid1", "title": "Video 1", "url": "u1",
        "content_type": "video", "status": "complete",
        "fetched_at": "2026-04-08T15:00:00Z",
    })

    yt_dir2 = tmp_output / "youtube" / "vid2"
    yt_dir2.mkdir(parents=True)
    write_json(yt_dir2 / "meta.json", {
        "id": "vid2", "title": "Video 2", "url": "u2",
        "content_type": "video", "status": "draft",
        "fetched_at": "2026-04-09T15:00:00Z",
    })

    indexer = Indexer(tmp_output)
    indexer.rebuild("youtube")

    from data_factory.core.storage import load_json
    index = load_json(tmp_output / "youtube" / "index.json")
    assert index["count"] == 2
    assert "vid1" in index["items"]
    assert "vid2" in index["items"]
