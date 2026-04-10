from data_factory.core.schema import FetchResult


def test_transcribe_should_skip_non_video(tmp_path):
    from data_factory.processors.transcribe import TranscribeProcessor

    proc = TranscribeProcessor()
    result = FetchResult("ok", "post", tmp_path, False)
    assert proc.should_run(result, tmp_path) is False


def test_transcribe_should_skip_completed(tmp_path):
    from data_factory.processors.transcribe import TranscribeProcessor
    from data_factory.core.storage import write_json

    write_json(tmp_path / "meta.json", {"transcript_completed": True})
    result = FetchResult("ok", "video", tmp_path, True)
    proc = TranscribeProcessor()
    assert proc.should_run(result, tmp_path) is False


def test_transcribe_should_run_for_video(tmp_path):
    from data_factory.processors.transcribe import TranscribeProcessor
    from data_factory.core.storage import write_json

    write_json(tmp_path / "meta.json", {"transcript_completed": False, "platform": "youtube"})
    result = FetchResult("ok", "video", tmp_path, True)
    proc = TranscribeProcessor()
    assert proc.should_run(result, tmp_path) is True


def test_transcribe_writes_transcript_json(tmp_path, mocker):
    from data_factory.processors.transcribe import TranscribeProcessor
    from data_factory.core.storage import write_json, load_json
    from data_factory.core.config import AppConfig, TranscribeConfig, WhisperApiConfig, WhisperLocalConfig, PlatformSubtitleConfig, NetworkConfig, SchedulerConfig, VideoConfig

    write_json(tmp_path / "meta.json", {
        "transcript_completed": False,
        "platform": "youtube",
        "url": "https://youtube.com/watch?v=abc",
        "files": {},
    })

    config = AppConfig(
        output_dir=tmp_path,
        log_level="info",
        transcribe=TranscribeConfig(
            whisper_api=WhisperApiConfig(False, "", "whisper-1", ""),
            whisper_local=WhisperLocalConfig(False, "large-v3", "cpu"),
            platform_subtitle=PlatformSubtitleConfig(True),
        ),
        platforms={},
        scheduler=SchedulerConfig(enabled=False),
        network=NetworkConfig(proxy="", timeout=30, retry=3),
        video=VideoConfig(quality="720p"),
    )

    mocker.patch(
        "data_factory.processors.transcribe.fetch_platform_subtitle",
        return_value={"method": "platform", "language": "en", "text": "Hello world", "segments": []},
    )

    result = FetchResult("ok", "video", tmp_path, True)
    proc = TranscribeProcessor()
    proc.process(result, tmp_path, config)

    transcript = load_json(tmp_path / "transcript.json")
    assert transcript is not None
    assert transcript["text"] == "Hello world"

    meta = load_json(tmp_path / "meta.json")
    assert meta["transcript_completed"] is True
