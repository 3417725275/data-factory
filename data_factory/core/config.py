"""Configuration loader. Single YAML file with env var overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class WhisperApiConfig:
    enabled: bool
    api_key: str
    model: str
    base_url: str


@dataclass
class WhisperLocalConfig:
    enabled: bool
    model_size: str
    device: str


@dataclass
class PlatformSubtitleConfig:
    enabled: bool


@dataclass
class TranscribeConfig:
    whisper_api: WhisperApiConfig
    whisper_local: WhisperLocalConfig
    platform_subtitle: PlatformSubtitleConfig


@dataclass
class PlatformConfig:
    enabled: bool
    rate_limit: float
    base_url: str | None = None
    token: str | None = None


@dataclass
class SchedulerJob:
    name: str
    platform: str
    action: str
    query: str
    cron: str
    limit: int = 10


@dataclass
class SchedulerConfig:
    enabled: bool
    jobs: list[SchedulerJob] = field(default_factory=list)


@dataclass
class NetworkConfig:
    proxy: str
    timeout: int
    retry: int


@dataclass
class VideoConfig:
    quality: str  # best, 1080p, 720p, 480p


@dataclass
class AppConfig:
    output_dir: Path
    log_level: str
    transcribe: TranscribeConfig
    platforms: dict[str, PlatformConfig]
    scheduler: SchedulerConfig
    network: NetworkConfig
    video: VideoConfig


def _parse_platform(name: str, raw: dict) -> PlatformConfig:
    return PlatformConfig(
        enabled=raw.get("enabled", True),
        rate_limit=float(raw.get("rate_limit", 1.0)),
        base_url=raw.get("base_url"),
        token=raw.get("token"),
    )


def _parse_scheduler(raw: dict) -> SchedulerConfig:
    jobs = []
    for j in raw.get("jobs", []):
        jobs.append(
            SchedulerJob(
                name=j["name"],
                platform=j["platform"],
                action=j.get("action", "search"),
                query=j.get("query", ""),
                cron=j["cron"],
                limit=int(j.get("limit", 10)),
            )
        )
    return SchedulerConfig(enabled=raw.get("enabled", False), jobs=jobs)


def _apply_env_overrides(config: AppConfig) -> None:
    key = os.environ.get("DATA_FACTORY_WHISPER_API_KEY")
    if key:
        config.transcribe.whisper_api.api_key = key

    proxy = os.environ.get("DATA_FACTORY_PROXY")
    if proxy:
        config.network.proxy = proxy

    out = os.environ.get("DATA_FACTORY_OUTPUT_DIR")
    if out:
        config.output_dir = Path(out)


def load_config(path: Path | None = None) -> AppConfig:
    if path is None:
        env_path = os.environ.get("DATA_FACTORY_CONFIG")
        if env_path:
            path = Path(env_path)
        else:
            path = Path("config.yaml")

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    t = raw.get("transcribe", {})
    wa = t.get("whisper_api", {})
    wl = t.get("whisper_local", {})
    ps = t.get("platform_subtitle", {})

    transcribe = TranscribeConfig(
        whisper_api=WhisperApiConfig(
            enabled=wa.get("enabled", False),
            api_key=wa.get("api_key", ""),
            model=wa.get("model", "whisper-1"),
            base_url=wa.get("base_url", "https://api.openai.com/v1"),
        ),
        whisper_local=WhisperLocalConfig(
            enabled=wl.get("enabled", False),
            model_size=wl.get("model_size", "large-v3"),
            device=wl.get("device", "cpu"),
        ),
        platform_subtitle=PlatformSubtitleConfig(
            enabled=ps.get("enabled", True),
        ),
    )

    platforms = {}
    for name, praw in raw.get("platforms", {}).items():
        platforms[name] = _parse_platform(name, praw)

    net = raw.get("network", {})
    network = NetworkConfig(
        proxy=net.get("proxy", ""),
        timeout=int(net.get("timeout", 30)),
        retry=int(net.get("retry", 3)),
    )

    vid = raw.get("video", {})
    video = VideoConfig(quality=vid.get("quality", "720p"))

    config = AppConfig(
        output_dir=Path(raw.get("output_dir", "./output")),
        log_level=raw.get("log_level", "info"),
        transcribe=transcribe,
        platforms=platforms,
        scheduler=_parse_scheduler(raw.get("scheduler", {})),
        network=network,
        video=video,
    )

    _apply_env_overrides(config)
    return config
