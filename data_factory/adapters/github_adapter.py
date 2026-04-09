"""GitHub adapter via REST API (no opencli)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import requests

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, maybe_write_text, maybe_write_json, now_iso

log = logging.getLogger(__name__)

API_BASE = "https://api.github.com"


def _parse_github_url(url: str) -> dict:
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)(?:/issues/(\d+))?", url)
    if m:
        return {"owner": m.group(1), "repo": m.group(2), "issue": m.group(3)}
    return {}


class GitHubAdapter(PlatformAdapter, adapter_name="github"):
    URL_PATTERNS = ["github.com"]

    def __init__(self, token: str | None = None, proxy: str = ""):
        self.token = token
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"token {token}"
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def search(self, query: str, limit: int = 20) -> list[str]:
        resp = self.session.get(
            f"{API_BASE}/search/repositories",
            params={"q": query, "per_page": min(limit, 30)},
            timeout=30,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [item["html_url"] for item in items[:limit]]

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        parsed = _parse_github_url(url)
        if not parsed.get("owner"):
            return FetchResult("error", "repo", output_dir, False, error=f"Cannot parse URL: {url}")

        owner, repo = parsed["owner"], parsed["repo"]
        issue_num = parsed.get("issue")

        if issue_num:
            return self._fetch_issue(owner, repo, issue_num, url, output_dir)
        return self._fetch_repo(owner, repo, url, output_dir)

    def _fetch_repo(self, owner: str, repo: str, url: str, output_dir: Path) -> FetchResult:
        try:
            resp = self.session.get(f"{API_BASE}/repos/{owner}/{repo}", timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return FetchResult("error", "repo", output_dir, False, error=str(e))

        try:
            readme_resp = self.session.get(
                f"{API_BASE}/repos/{owner}/{repo}/readme",
                headers={"Accept": "application/vnd.github.raw"},
                timeout=30,
            )
            readme = readme_resp.text if readme_resp.status_code == 200 else ""
        except Exception:
            readme = ""

        content_file = maybe_write_text(output_dir / "content.md", readme)

        item_id = f"{owner}_{repo}"

        files: dict = {"assets": []}
        if content_file:
            files["content"] = content_file

        meta = {
            "id": item_id,
            "platform": "github",
            "url": url,
            "content_type": "repo",
            "fetch_method": "api",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": data.get("full_name", f"{owner}/{repo}"),
            "author": owner,
            "published_at": data.get("created_at", ""),
            "language": data.get("language", ""),
            "content_fetched": bool(readme and readme.strip()),
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": files,
            "comments_refresh": None,
            "comment_history": [],
            "platform_meta": {
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "description": data.get("description", ""),
                "topics": data.get("topics", []),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "repo", output_dir, False)

    def _fetch_issue(self, owner: str, repo: str, issue_num: str, url: str, output_dir: Path) -> FetchResult:
        try:
            resp = self.session.get(
                f"{API_BASE}/repos/{owner}/{repo}/issues/{issue_num}",
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return FetchResult("error", "issue", output_dir, False, error=str(e))

        content = f"# {data.get('title', '')}\n\n{data.get('body', '')}"
        content_file = maybe_write_text(output_dir / "content.md", content)

        comments = self.fetch_comments(url)
        comments_file = maybe_write_json(output_dir / "comments.json", comments)

        from datetime import datetime, timedelta, timezone

        refresh_state = {
            "current_interval_days": 1,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": len(comments),
        }

        item_id = f"{owner}_{repo}_issue_{issue_num}"

        files: dict = {"assets": []}
        if content_file:
            files["content"] = content_file
        if comments_file:
            files["comments"] = comments_file

        meta = {
            "id": item_id,
            "platform": "github",
            "url": url,
            "content_type": "issue",
            "fetch_method": "api",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": data.get("title", ""),
            "author": data.get("user", {}).get("login", ""),
            "published_at": data.get("created_at", ""),
            "language": "",
            "content_fetched": bool(content_file),
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": files,
            "comments_refresh": refresh_state,
            "comment_history": [{"timestamp": now_iso(), "count": len(comments)}],
            "platform_meta": {
                "state": data.get("state", ""),
                "labels": [l["name"] for l in data.get("labels", [])],
                "reactions": data.get("reactions", {}).get("total_count", 0),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "issue", output_dir, False)

    def fetch_comments(self, url: str) -> list[dict]:
        parsed = _parse_github_url(url)
        if not parsed.get("issue"):
            return []
        owner, repo, issue_num = parsed["owner"], parsed["repo"], parsed["issue"]

        all_comments = []
        page = 1
        while True:
            resp = self.session.get(
                f"{API_BASE}/repos/{owner}/{repo}/issues/{issue_num}/comments",
                params={"per_page": 100, "page": page},
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            all_comments.extend(batch)
            if len(batch) < 100:
                break
            page += 1

        return all_comments
