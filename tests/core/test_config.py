import pytest
from pathlib import Path


def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        """
output_dir: "./data"
log_level: "debug"
transcribe:
  whisper_api:
    enabled: true
    api_key: "sk-test"
    model: "whisper-1"
    base_url: "https://api.openai.com/v1"
  whisper_local:
    enabled: false
    model_size: "large-v3"
    device: "cpu"
  platform_subtitle:
    enabled: true
platforms:
  youtube:
    enabled: true
    rate_limit: 2.0
  github:
    enabled: false
    token: "ghp_xxx"
    rate_limit: 1.0
scheduler:
  enabled: false
  jobs: []
network:
  proxy: ""
  timeout: 30
  retry: 3
""",
        encoding="utf-8",
    )

    from data_factory.core.config import load_config

    config = load_config(cfg_file)

    assert config.output_dir == Path("./data")
    assert config.log_level == "debug"
    assert config.transcribe.whisper_api.enabled is True
    assert config.transcribe.whisper_api.api_key == "sk-test"
    assert config.transcribe.whisper_local.enabled is False
    assert config.platforms["youtube"].enabled is True
    assert config.platforms["youtube"].rate_limit == 2.0
    assert config.platforms["github"].enabled is False
    assert config.platforms["github"].token == "ghp_xxx"
    assert config.network.timeout == 30


def test_load_config_missing_file():
    from data_factory.core.config import load_config

    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))


def test_load_config_env_override(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        """
output_dir: "./data"
log_level: "info"
transcribe:
  whisper_api:
    enabled: true
    api_key: "old-key"
    model: "whisper-1"
    base_url: "https://api.openai.com/v1"
  whisper_local:
    enabled: false
    model_size: "large-v3"
    device: "cpu"
  platform_subtitle:
    enabled: true
platforms: {}
scheduler:
  enabled: false
  jobs: []
network:
  proxy: ""
  timeout: 30
  retry: 3
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("DATA_FACTORY_WHISPER_API_KEY", "sk-env-override")

    from data_factory.core.config import load_config

    config = load_config(cfg_file)
    assert config.transcribe.whisper_api.api_key == "sk-env-override"


def test_platform_config_defaults():
    from data_factory.core.config import PlatformConfig

    pc = PlatformConfig(enabled=True, rate_limit=1.0)
    assert pc.base_url is None
    assert pc.token is None
