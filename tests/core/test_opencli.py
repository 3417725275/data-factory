import json
import subprocess


def test_run_opencli_returns_parsed_json(mocker):
    from data_factory.core.opencli import run_opencli

    mock_result = mocker.MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps([
        {"rank": 1, "title": "Video A", "url": "https://youtube.com/watch?v=aaa"},
        {"rank": 2, "title": "Video B", "url": "https://youtube.com/watch?v=bbb"},
    ])
    mocker.patch("subprocess.run", return_value=mock_result)

    result = run_opencli("youtube", "search", ["LLM tutorial", "--limit", "2"])

    assert len(result) == 2
    assert result[0]["title"] == "Video A"

    subprocess.run.assert_called_once()
    call_args = subprocess.run.call_args[0][0]
    assert call_args[0] == "opencli"
    assert "youtube" in call_args
    assert "search" in call_args
    assert "-f" in call_args
    assert "json" in call_args


def test_run_opencli_raises_on_failure(mocker):
    import pytest
    from data_factory.core.opencli import run_opencli, OpencliError

    mock_result = mocker.MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Command failed"
    mocker.patch("subprocess.run", return_value=mock_result)

    with pytest.raises(OpencliError, match="Command failed"):
        run_opencli("youtube", "search", ["bad query"])


def test_run_opencli_handles_table_output_gracefully(mocker):
    from data_factory.core.opencli import run_opencli

    mock_result = mocker.MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"field": "title", "value": "My Video"})
    mocker.patch("subprocess.run", return_value=mock_result)

    result = run_opencli("youtube", "video", ["https://youtube.com/watch?v=xxx"])
    assert result["field"] == "title"
