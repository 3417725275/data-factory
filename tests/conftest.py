import pytest
from pathlib import Path


@pytest.fixture
def tmp_output(tmp_path):
    """Temporary output directory for tests."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def sample_config_dict():
    """Minimal config dictionary for tests."""
    return {
        "output_dir": "./output",
        "log_level": "info",
        "transcribe": {
            "whisper_api": {
                "enabled": False,
                "api_key": "",
                "model": "whisper-1",
                "base_url": "https://api.openai.com/v1",
            },
            "whisper_local": {
                "enabled": False,
                "model_size": "large-v3",
                "device": "cpu",
            },
            "platform_subtitle": {"enabled": True},
        },
        "platforms": {
            "youtube": {"enabled": True, "rate_limit": 2.0},
        },
        "scheduler": {"enabled": False, "jobs": []},
        "network": {"proxy": "", "timeout": 30, "retry": 3},
    }
