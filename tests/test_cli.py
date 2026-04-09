from click.testing import CliRunner


def test_cli_index_status(tmp_path, mocker):
    from data_factory.cli import main
    from data_factory.core.storage import write_json

    yt_dir = tmp_path / "output" / "youtube"
    yt_dir.mkdir(parents=True)
    write_json(yt_dir / "index.json", {
        "platform": "youtube", "count": 3, "updated_at": "2026-04-08",
        "items": {
            "a": {"status": "complete"}, "b": {"status": "complete"}, "c": {"status": "draft"},
        },
    })
    write_json(tmp_path / "output" / "global_index.json", {
        "updated_at": "2026-04-08", "total_count": 3,
        "platforms": {"youtube": {"count": 3, "last_updated": "2026-04-08"}},
    })

    cfg_file = tmp_path / "config.yaml"
    cfg_content = 'output_dir: "' + str(tmp_path / "output").replace("\\", "/") + '"\n'
    cfg_content += """log_level: info
transcribe:
  whisper_api:
    enabled: false
    api_key: ""
    model: whisper-1
    base_url: https://api.openai.com/v1
  whisper_local:
    enabled: false
    model_size: large-v3
    device: cpu
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
"""
    cfg_file.write_text(cfg_content, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["--config", str(cfg_file), "index", "status"])
    assert result.exit_code == 0
    assert "youtube" in result.output
    assert "3" in result.output
