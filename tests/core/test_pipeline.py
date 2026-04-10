import json
from pathlib import Path
from unittest.mock import MagicMock

from data_factory.core.schema import FetchResult


def test_pipeline_run_full_new_item(tmp_path, mocker):
    from data_factory.core.pipeline import Pipeline
    from data_factory.core.config import AppConfig, TranscribeConfig, WhisperApiConfig, WhisperLocalConfig, PlatformSubtitleConfig, NetworkConfig, SchedulerConfig, VideoConfig

    config = AppConfig(
        output_dir=tmp_path / "output",
        log_level="info",
        transcribe=TranscribeConfig(
            whisper_api=WhisperApiConfig(False, "", "whisper-1", ""),
            whisper_local=WhisperLocalConfig(False, "large-v3", "cpu"),
            platform_subtitle=PlatformSubtitleConfig(True),
        ),
        platforms={"youtube": MagicMock(enabled=True, rate_limit=2.0)},
        scheduler=SchedulerConfig(enabled=False),
        network=NetworkConfig(proxy="", timeout=30, retry=3),
        video=VideoConfig(quality="720p"),
    )

    output_dir = tmp_path / "output" / "youtube" / "abc123"
    mock_adapter = MagicMock()
    mock_adapter.fetch.return_value = FetchResult(
        status="ok", content_type="video", output_dir=output_dir,
        needs_transcribe=True,
    )

    mocker.patch("data_factory.core.pipeline.get_adapter", return_value=mock_adapter)

    output_dir.mkdir(parents=True)
    from data_factory.core.storage import write_json
    write_json(output_dir / "meta.json", {
        "id": "abc123", "platform": "youtube", "url": "u",
        "content_type": "video", "status": "draft",
        "fetched_at": "2026-04-08T00:00:00Z", "title": "T",
    })

    pipeline = Pipeline(config)
    pipeline.run_full("https://youtube.com/watch?v=abc123", "youtube")

    mock_adapter.fetch.assert_called_once()


def test_pipeline_run_refresh_updates_comments(tmp_path, mocker):
    from data_factory.core.pipeline import Pipeline
    from data_factory.core.config import AppConfig, TranscribeConfig, WhisperApiConfig, WhisperLocalConfig, PlatformSubtitleConfig, NetworkConfig, SchedulerConfig, VideoConfig
    from data_factory.core.storage import write_json, load_json

    config = AppConfig(
        output_dir=tmp_path / "output",
        log_level="info",
        transcribe=TranscribeConfig(
            whisper_api=WhisperApiConfig(False, "", "whisper-1", ""),
            whisper_local=WhisperLocalConfig(False, "large-v3", "cpu"),
            platform_subtitle=PlatformSubtitleConfig(True),
        ),
        platforms={"youtube": MagicMock(enabled=True, rate_limit=2.0)},
        scheduler=SchedulerConfig(enabled=False),
        network=NetworkConfig(proxy="", timeout=30, retry=3),
        video=VideoConfig(quality="720p"),
    )

    output_dir = tmp_path / "output" / "youtube" / "abc123"
    output_dir.mkdir(parents=True)
    write_json(output_dir / "meta.json", {
        "id": "abc123", "platform": "youtube", "url": "https://youtube.com/watch?v=abc123",
        "content_type": "video", "status": "complete", "title": "T",
        "fetched_at": "2026-04-08T00:00:00Z",
        "content_fetched": True,
        "comments_refresh": {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": "2020-01-01T00:00:00Z",
            "last_refresh_at": "2020-01-01T00:00:00Z",
            "last_comment_count": 5,
        },
        "comment_history": [{"timestamp": "2020-01-01T00:00:00Z", "count": 5}],
    })
    write_json(output_dir / "comments.json", [])

    mock_adapter = MagicMock()
    mock_adapter.fetch_comments.return_value = [
        {"author": "A", "text": "new comment"},
        {"author": "B", "text": "another"},
    ]
    mocker.patch("data_factory.core.pipeline.get_adapter", return_value=mock_adapter)

    pipeline = Pipeline(config)
    pipeline.run_refresh("https://youtube.com/watch?v=abc123", "youtube")

    mock_adapter.fetch_comments.assert_called_once()
    comments = load_json(output_dir / "comments.json")
    assert len(comments) == 2

    meta = load_json(output_dir / "meta.json")
    assert len(meta["comment_history"]) == 2
    assert meta["comment_history"][-1]["count"] == 2
