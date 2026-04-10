from unittest.mock import MagicMock


def test_scheduler_creates_jobs_from_config():
    from data_factory.core.scheduler import DataFactoryScheduler
    from data_factory.core.config import SchedulerConfig, SchedulerJob, AppConfig, TranscribeConfig, WhisperApiConfig, WhisperLocalConfig, PlatformSubtitleConfig, NetworkConfig, VideoConfig

    config = AppConfig(
        output_dir=MagicMock(),
        log_level="info",
        transcribe=TranscribeConfig(
            WhisperApiConfig(False, "", "", ""),
            WhisperLocalConfig(False, "", ""),
            PlatformSubtitleConfig(True),
        ),
        platforms={},
        scheduler=SchedulerConfig(
            enabled=True,
            jobs=[
                SchedulerJob("yt-daily", "youtube", "search", "AI", "0 8 * * *", 10),
                SchedulerJob("reddit-weekly", "reddit", "search", "ML", "0 9 * * 1", 20),
            ],
        ),
        network=NetworkConfig("", 30, 3),
        video=VideoConfig(quality="720p"),
    )

    pipeline = MagicMock()
    scheduler = DataFactoryScheduler(config, pipeline)

    assert len(scheduler.job_configs) == 2
    assert scheduler.job_configs[0].name == "yt-daily"
