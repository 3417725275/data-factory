"""Wrapper for calling opencli CLI commands."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"


class OpencliError(RuntimeError):
    pass


def _resolve_opencli() -> str:
    """Resolve the full path to the opencli executable."""
    path = shutil.which("opencli")
    if path is None:
        raise OpencliError(
            "opencli not found. Install it with: npm install -g @jackwener/opencli\n"
            "Then run: opencli doctor"
        )
    return path


def run_opencli(
    platform: str,
    command: str,
    args: list[str] | None = None,
    format: str = "json",
    timeout: int = 300,
    proxy: str = "",
) -> dict | list:
    opencli_bin = _resolve_opencli()
    cmd = [opencli_bin, platform, command]
    if args:
        cmd.extend(args)
    cmd.extend(["-f", format])

    log.debug("Running: %s", " ".join(cmd))

    env = None
    if proxy:
        env = {**os.environ, "HTTP_PROXY": proxy, "HTTPS_PROXY": proxy}

    if _IS_WINDOWS:
        cmd_str = " ".join(f'"{c}"' for c in cmd)
        result = subprocess.run(
            cmd_str,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            shell=True,
            encoding="utf-8",
            errors="replace",
        )
    else:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            encoding="utf-8",
            errors="replace",
        )

    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        raise OpencliError(
            f"opencli {platform} {command} failed (exit {result.returncode}): {msg}"
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise OpencliError(
            f"Failed to parse opencli output as JSON: {e}\nOutput: {result.stdout[:500]}"
        ) from e
