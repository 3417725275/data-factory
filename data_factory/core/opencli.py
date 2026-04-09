"""Wrapper for calling opencli CLI commands."""

from __future__ import annotations

import json
import logging
import subprocess

log = logging.getLogger(__name__)


class OpencliError(RuntimeError):
    pass


def run_opencli(
    platform: str,
    command: str,
    args: list[str] | None = None,
    format: str = "json",
    timeout: int = 120,
    proxy: str = "",
) -> dict | list:
    cmd = ["opencli", platform, command]
    if args:
        cmd.extend(args)
    cmd.extend(["-f", format])

    log.debug("Running: %s", " ".join(cmd))

    env = None
    if proxy:
        import os
        env = {**os.environ, "HTTP_PROXY": proxy, "HTTPS_PROXY": proxy}

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
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
