from data_factory.core.schema import FetchResult


def test_images_should_skip_if_already_downloaded(tmp_path):
    from data_factory.processors.images import ImageDownloadProcessor
    from data_factory.core.storage import write_json

    write_json(tmp_path / "meta.json", {"images_downloaded": True})
    result = FetchResult("ok", "post", tmp_path, False)
    proc = ImageDownloadProcessor()
    assert proc.should_run(result, tmp_path) is False


def test_images_should_run_if_not_downloaded(tmp_path):
    from data_factory.processors.images import ImageDownloadProcessor
    from data_factory.core.storage import write_json

    write_json(tmp_path / "meta.json", {"images_downloaded": False})
    result = FetchResult("ok", "post", tmp_path, False)
    proc = ImageDownloadProcessor()
    assert proc.should_run(result, tmp_path) is True


def test_images_downloads_from_platform_meta(tmp_path, mocker):
    from data_factory.processors.images import ImageDownloadProcessor
    from data_factory.core.storage import write_json, load_json
    from data_factory.core.config import AppConfig, TranscribeConfig, WhisperApiConfig, WhisperLocalConfig, PlatformSubtitleConfig, NetworkConfig, SchedulerConfig

    write_json(tmp_path / "meta.json", {
        "images_downloaded": False,
        "platform_meta": {
            "thumbnail_url": "https://example.com/thumb.jpg",
        },
        "files": {"assets": []},
    })

    config = AppConfig(
        output_dir=tmp_path,
        log_level="info",
        transcribe=TranscribeConfig(
            WhisperApiConfig(False, "", "", ""),
            WhisperLocalConfig(False, "", ""),
            PlatformSubtitleConfig(True),
        ),
        platforms={},
        scheduler=SchedulerConfig(enabled=False),
        network=NetworkConfig(proxy="", timeout=30, retry=3),
    )

    mocker.patch("data_factory.processors.images.download_file", return_value=True)

    result = FetchResult("ok", "post", tmp_path, False)
    proc = ImageDownloadProcessor()
    proc.process(result, tmp_path, config)

    meta = load_json(tmp_path / "meta.json")
    assert meta["images_downloaded"] is True
