"""Zhihu adapter via opencli."""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path

from data_factory.adapters.base import PlatformAdapter
from data_factory.core.opencli import run_opencli
from data_factory.core.schema import FetchResult
from data_factory.core.storage import write_json, write_text, now_iso

log = logging.getLogger(__name__)

_UI_NOISE_PATTERNS = [
    re.compile(r"^复制为Markdown.*$", re.MULTILINE),
    re.compile(r"^下载为\s*(ZIP|纯文本).*$", re.MULTILINE),
    re.compile(r"^剪藏为\s*PNG.*$", re.MULTILINE),
    re.compile(r"^保存到\s*$", re.MULTILINE),
    re.compile(r"^指定文件夹\s*$", re.MULTILINE),
    re.compile(r"^\s*保存评论\s*$", re.MULTILINE),
    re.compile(r"^\s*保存到\s*指定文件夹\s*$", re.MULTILINE),
]


def _extract_zhihu_id(url: str) -> str:
    m = re.search(r"question/(\d+)", url)
    if m:
        return f"q_{m.group(1)}"
    m = re.search(r"answer/(\d+)", url)
    if m:
        return f"a_{m.group(1)}"
    m = re.search(r"p/(\d+)", url)
    if m:
        return f"p_{m.group(1)}"
    return url.rstrip("/").split("/")[-1]


def _detect_content_type(url: str) -> str:
    if "question" in url:
        return "question"
    if "/p/" in url or "zhuanlan" in url:
        return "article"
    return "article"


def _clean_content(text: str) -> str:
    """Remove UI noise captured by opencli from article content."""
    for pat in _UI_NOISE_PATTERNS:
        text = pat.sub("", text)
    lines = text.split("\n")
    cleaned = []
    blank_streak = 0
    for line in lines:
        if line.strip() == "":
            blank_streak += 1
            if blank_streak <= 2:
                cleaned.append(line)
        else:
            blank_streak = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip() + "\n"


def _discover_opencli_cdp_port() -> int | None:
    """Find the CDP debugging port of opencli's Chrome by inspecting process args."""
    import sys
    try:
        if sys.platform == "win32":
            import subprocess
            result = subprocess.run(
                ["wmic", "process", "where", "name='chrome.exe'", "get", "CommandLine"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
            for line in result.stdout.splitlines():
                if "openclaw" in line.lower() or "qclaw" in line.lower():
                    m = re.search(r"--remote-debugging-port=(\d+)", line)
                    if m:
                        return int(m.group(1))
        else:
            import subprocess
            result = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "chrome" in line and ("openclaw" in line or "qclaw" in line):
                    m = re.search(r"--remote-debugging-port=(\d+)", line)
                    if m:
                        return int(m.group(1))
    except Exception as e:
        log.debug("Failed to discover CDP port: %s", e)
    return None


def _fetch_title_via_cdp(url: str) -> str:
    """Extract question title by connecting to opencli's Chrome via CDP."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.debug("playwright not installed, skipping CDP title extraction")
        return ""

    port = _discover_opencli_cdp_port()
    if not port:
        log.debug("opencli Chrome CDP port not found")
        return ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(
                f"http://127.0.0.1:{port}", timeout=5000
            )
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            h1 = page.query_selector("h1.QuestionHeader-title")
            title = h1.inner_text().strip() if h1 else ""
            if not title:
                raw_title = page.title()
                title = re.sub(r"\s*[-–—]\s*知乎$", "", raw_title).strip()
                if title == "知乎":
                    title = ""
            page.close()
            browser.close()
            return title
    except Exception as e:
        log.debug("CDP title extraction failed: %s", e)
        return ""


def _fetch_question_title(url: str) -> str:
    """Extract question title via CDP (preferred) or HTTP fallback."""
    title = _fetch_title_via_cdp(url)
    if title:
        return title
    try:
        import requests
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, allow_redirects=True)
        if resp.status_code == 200:
            m = re.search(r"<title[^>]*>(.+?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
            if m:
                title = m.group(1).strip()
                title = re.sub(r"\s*[-–—]\s*知乎$", "", title)
                if title and title != "知乎":
                    return title
    except Exception as e:
        log.debug("Failed to fetch question title via HTTP: %s", e)
    return ""


def _summarize_as_title(answers: list[dict], question_id: str) -> str:
    """Generate a readable title from answers when question title is unavailable."""
    if not answers:
        return f"知乎问题 {question_id}"
    first = answers[0].get("content", "")
    first = first.replace("\n", " ").strip()
    if len(first) > 60:
        cut = first[:60]
        last_punct = max(cut.rfind("。"), cut.rfind("，"), cut.rfind("；"), cut.rfind("！"), cut.rfind("？"), cut.rfind(". "))
        if last_punct > 20:
            return cut[:last_punct + 1] + "…"
        return cut + "…"
    return first or f"知乎问题 {question_id}"


def _flatten_assets(assets_dir: Path):
    """Move files from subdirectories up to assets_dir root, then remove empty subdirs."""
    if not assets_dir.exists():
        return
    for sub in [d for d in assets_dir.iterdir() if d.is_dir()]:
        for f in sub.rglob("*"):
            if f.is_file():
                dest = assets_dir / f.name
                if not dest.exists():
                    shutil.move(str(f), str(dest))
        shutil.rmtree(sub, ignore_errors=True)


class ZhihuAdapter(PlatformAdapter, adapter_name="zhihu"):
    URL_PATTERNS = ["zhihu.com"]

    def search(self, query: str, limit: int = 20) -> list[str]:
        results = run_opencli("zhihu", "search", [query, "--limit", str(limit)])
        urls = [item["url"] for item in results if "url" in item]
        self._cache_search_titles(results)
        return urls

    def _get_cache_path(self) -> Path:
        """Resolve the search cache path from AppConfig."""
        try:
            from data_factory.core.config import AppConfig
            config = AppConfig.load()
            return Path(config.output_dir) / "zhihu" / ".search_cache.json"
        except Exception:
            return Path("zhihu") / ".search_cache.json"

    def _cache_search_titles(self, results: list[dict]):
        """Save URL->title mapping from search results for later use by fetch."""
        if not results:
            return
        cache_path = self._get_cache_path()
        cache: dict[str, str] = {}
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        for item in results:
            url = item.get("url", "")
            title = item.get("title", "")
            if url and title:
                qid_match = re.search(r"question/(\d+)", url)
                if qid_match:
                    cache[f"q_{qid_match.group(1)}"] = title
                cache[url] = title

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _lookup_cached_title(cache_path: Path, zhihu_id: str, url: str) -> str:
        """Look up title from search cache."""
        if not cache_path.exists():
            return ""
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            return cache.get(zhihu_id, cache.get(url, ""))
        except Exception:
            return ""

    def fetch(self, url: str, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        zhihu_id = _extract_zhihu_id(url)
        content_type = _detect_content_type(url)

        if content_type == "article":
            return self._fetch_article(url, output_dir, zhihu_id)

        return self._fetch_question(url, output_dir, zhihu_id)

    def _fetch_article(self, url: str, output_dir: Path, zhihu_id: str) -> FetchResult:
        """Fetch a zhihu zhuanlan article using opencli zhihu download."""
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)

        try:
            raw = run_opencli("zhihu", "download", [
                "--url", url, "--output", str(assets_dir),
            ])
        except Exception as e:
            return FetchResult("error", "article", output_dir, False, error=str(e))

        info = {}
        if isinstance(raw, list) and raw:
            info = raw[0] if isinstance(raw[0], dict) else {}
        elif isinstance(raw, dict):
            info = raw

        _flatten_assets(assets_dir)

        content = ""
        md_files = list(assets_dir.glob("*.md"))
        if md_files:
            content = md_files[0].read_text(encoding="utf-8")
            content = _clean_content(content)

        if not content and info:
            content = info.get("content", info.get("title", ""))

        write_text(output_dir / "content.md", content)
        write_json(output_dir / "comments.json", [])

        from datetime import datetime, timedelta, timezone
        refresh_state = {
            "current_interval_days": 14,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": 0,
        }

        title = info.get("title", "")
        if not title or title == "untitled":
            first_line = content.split("\n")[0].strip() if content else ""
            if first_line.startswith("#"):
                title = first_line.lstrip("# ").strip()

        meta = {
            "id": zhihu_id,
            "platform": "zhihu",
            "url": url,
            "content_type": "article",
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": title,
            "author": info.get("author", ""),
            "published_at": info.get("publish_time", ""),
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"content": "content.md", "comments": "comments.json", "assets": []},
            "comments_refresh": refresh_state,
            "comment_history": [],
            "platform_meta": {
                "article_id": zhihu_id,
                "size": info.get("size", ""),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "article", output_dir, False)

    def _fetch_question(self, url: str, output_dir: Path, zhihu_id: str) -> FetchResult:
        """Fetch a zhihu question: title from page, answers from opencli."""
        m = re.search(r"question/(\d+)", url)
        if not m:
            return FetchResult("error", "question", output_dir, False,
                               error=f"Cannot extract numeric question ID from: {url}")
        question_id = m.group(1)

        cache_path = self._get_cache_path()
        if not cache_path.exists():
            cache_path = output_dir.parent / ".search_cache.json"
        title = self._lookup_cached_title(cache_path, f"q_{question_id}", url)
        if not title:
            question_url = f"https://www.zhihu.com/question/{question_id}"
            title = _fetch_question_title(question_url)

        try:
            raw = run_opencli("zhihu", "question", [question_id, "--limit", "10"])
        except Exception as e:
            return FetchResult("error", "question", output_dir, False, error=str(e))

        answers = []
        if isinstance(raw, list):
            answers = [r for r in raw if isinstance(r, dict)]
        elif isinstance(raw, dict):
            answers = [raw]

        parts = []
        authors = []
        for ans in answers:
            author = ans.get("author", "anonymous")
            votes = ans.get("votes", 0)
            text = ans.get("content", "")
            authors.append(author)
            parts.append(f"## 回答 by {author} (赞同: {votes})\n\n{text}")

        header = f"# {title}\n\n" if title else f"# 知乎问题 {question_id}\n\n"
        content = header + "\n\n---\n\n".join(parts) if parts else header
        write_text(output_dir / "content.md", content)

        write_json(output_dir / "answers.json", answers)

        comments = []
        log.warning("Zhihu comments not available via opencli for %s", url)
        write_json(output_dir / "comments.json", comments)

        if not title:
            title = _summarize_as_title(answers, question_id)

        from datetime import datetime, timedelta, timezone
        refresh_state = {
            "current_interval_days": 14,
            "consecutive_unchanged": 0,
            "next_refresh_at": (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_at": now_iso(),
            "last_comment_count": 0,
        }

        meta = {
            "id": zhihu_id,
            "platform": "zhihu",
            "url": url,
            "content_type": "question",
            "fetch_method": "opencli",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": title,
            "author": authors[0] if authors else "",
            "published_at": "",
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"content": "content.md", "answers": "answers.json", "comments": "comments.json", "assets": []},
            "comments_refresh": refresh_state,
            "comment_history": [],
            "platform_meta": {
                "question_id": question_id,
                "answer_count": len(answers),
            },
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "question", output_dir, False)

    def fetch_comments(self, url: str) -> list[dict]:
        log.warning("Zhihu comments not available via opencli")
        return []

    def import_file(self, file_path: Path, output_dir: Path) -> FetchResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        import json
        data = json.loads(file_path.read_text(encoding="utf-8"))

        content = data.get("content", "")
        write_text(output_dir / "content.md", content)
        write_json(output_dir / "comments.json", data.get("comments", []))

        meta = {
            "id": data.get("id", file_path.stem),
            "platform": "zhihu",
            "url": data.get("url", ""),
            "content_type": data.get("content_type", "article"),
            "fetch_method": "import",
            "fetched_at": now_iso(),
            "status": "complete",
            "title": data.get("title", ""),
            "author": data.get("author", ""),
            "published_at": data.get("created", ""),
            "language": "zh",
            "content_fetched": True,
            "content_fetched_at": now_iso(),
            "transcript_completed": False,
            "images_downloaded": False,
            "files": {"content": "content.md", "comments": "comments.json", "assets": []},
            "comments_refresh": None,
            "comment_history": [],
            "platform_meta": data.get("platform_meta", {}),
        }
        write_json(output_dir / "meta.json", meta)
        return FetchResult("ok", "article", output_dir, False)
