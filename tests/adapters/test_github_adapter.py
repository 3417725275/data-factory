import json
from pathlib import Path


def test_github_can_fetch():
    from data_factory.adapters.github_adapter import GitHubAdapter

    adapter = GitHubAdapter()
    assert adapter.can_fetch("https://github.com/owner/repo")
    assert adapter.can_fetch("https://github.com/owner/repo/issues/42")
    assert not adapter.can_fetch("https://youtube.com/watch?v=abc")


def test_github_search(mocker):
    from data_factory.adapters.github_adapter import GitHubAdapter

    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = {"items": [{"html_url": "https://github.com/owner/repo"}]}
    mocker.patch("data_factory.adapters.github_adapter.requests.get", return_value=mock_resp)

    adapter = GitHubAdapter()
    urls = adapter.search("python web framework", limit=5)
    assert len(urls) == 1


def test_github_fetch_repo(mocker, tmp_path):
    from data_factory.adapters.github_adapter import GitHubAdapter

    repo_data = {
        "full_name": "owner/repo",
        "stargazers_count": 1000,
        "forks_count": 100,
        "open_issues_count": 50,
        "description": "A test repo",
        "language": "Python",
        "created_at": "2025-01-01",
        "topics": ["python"],
    }

    def mock_get(url, **kwargs):
        resp = mocker.MagicMock()
        if "/readme" in url:
            resp.status_code = 200
            resp.text = "# README content"
        else:
            resp.status_code = 200
            resp.json.return_value = repo_data
        return resp

    mocker.patch("data_factory.adapters.github_adapter.requests.get", side_effect=mock_get)

    output_dir = tmp_path / "github" / "owner_repo"
    adapter = GitHubAdapter()
    result = adapter.fetch("https://github.com/owner/repo", output_dir)

    assert result.status == "ok"
    assert result.content_type == "repo"
    assert (output_dir / "meta.json").exists()
    assert (output_dir / "content.md").exists()
    meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["platform"] == "github"
    assert meta["platform_meta"]["stars"] == 1000


def test_github_fetch_issue(mocker, tmp_path):
    from data_factory.adapters.github_adapter import GitHubAdapter

    issue_data = {
        "title": "Bug report",
        "body": "Something is broken",
        "user": {"login": "reporter"},
        "created_at": "2026-01-01",
        "state": "open",
        "labels": [{"name": "bug"}],
        "reactions": {"total_count": 5},
    }

    def mock_get(url, **kwargs):
        resp = mocker.MagicMock()
        if "/comments" in url:
            resp.json.return_value = [{"body": "Comment 1", "user": {"login": "user1"}}]
        else:
            resp.json.return_value = issue_data
        return resp

    mocker.patch("data_factory.adapters.github_adapter.requests.get", side_effect=mock_get)

    output_dir = tmp_path / "github" / "owner_repo_issue_42"
    adapter = GitHubAdapter()
    result = adapter.fetch("https://github.com/owner/repo/issues/42", output_dir)

    assert result.status == "ok"
    assert result.content_type == "issue"
    assert (output_dir / "meta.json").exists()
    meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["platform"] == "github"
    assert meta["title"] == "Bug report"
