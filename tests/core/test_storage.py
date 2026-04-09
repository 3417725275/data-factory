import json
from pathlib import Path


def test_write_json_and_load_json(tmp_path):
    from data_factory.core.storage import write_json, load_json

    data = {"id": "abc123", "title": "Test", "count": 42}
    path = tmp_path / "test.json"

    write_json(path, data)
    assert path.exists()

    loaded = load_json(path)
    assert loaded == data


def test_write_json_creates_parent_dirs(tmp_path):
    from data_factory.core.storage import write_json

    path = tmp_path / "deep" / "nested" / "test.json"
    write_json(path, {"key": "value"})
    assert path.exists()


def test_load_json_missing_returns_none(tmp_path):
    from data_factory.core.storage import load_json

    result = load_json(tmp_path / "nonexistent.json")
    assert result is None


def test_write_text_and_read_text(tmp_path):
    from data_factory.core.storage import write_text, read_text

    path = tmp_path / "content.txt"
    write_text(path, "Hello, world!\n第二行")

    assert read_text(path) == "Hello, world!\n第二行"


def test_read_text_missing_returns_none(tmp_path):
    from data_factory.core.storage import read_text

    result = read_text(tmp_path / "nonexistent.txt")
    assert result is None


def test_update_meta(tmp_path):
    from data_factory.core.storage import write_json, load_json, update_meta

    meta_path = tmp_path / "meta.json"
    write_json(meta_path, {"id": "abc", "status": "draft", "files": {}})

    update_meta(tmp_path, {"status": "complete", "transcript_completed": True})

    loaded = load_json(meta_path)
    assert loaded["status"] == "complete"
    assert loaded["transcript_completed"] is True
    assert loaded["id"] == "abc"


def test_now_iso():
    from data_factory.core.storage import now_iso

    ts = now_iso()
    assert "T" in ts
    assert ts.endswith("Z")
