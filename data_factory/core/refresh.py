"""Comment refresh backoff algorithm."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from data_factory.core.schema import CommentsRefreshState

BACKOFF_SCHEDULE = [
    (2, 3),   # after 2 consecutive unchanged → 3 day interval
    (1, 7),   # after 1 more → 7 day interval
    (1, 14),  # after 1 more → 14 day interval (cap)
]


def compute_next_refresh(
    current_count: int,
    refresh_state: CommentsRefreshState,
) -> CommentsRefreshState:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    changed = current_count != refresh_state.last_comment_count

    if changed:
        next_at = datetime.now(timezone.utc) + timedelta(days=1)
        return CommentsRefreshState(
            current_interval_days=1,
            consecutive_unchanged=0,
            next_refresh_at=next_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            last_refresh_at=now,
            last_comment_count=current_count,
        )

    new_unchanged = refresh_state.consecutive_unchanged + 1
    new_interval = 1

    threshold_acc = 0
    for threshold, interval in BACKOFF_SCHEDULE:
        threshold_acc += threshold
        if new_unchanged >= threshold_acc:
            new_interval = interval

    next_at = datetime.now(timezone.utc) + timedelta(days=new_interval)
    return CommentsRefreshState(
        current_interval_days=new_interval,
        consecutive_unchanged=new_unchanged,
        next_refresh_at=next_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        last_refresh_at=now,
        last_comment_count=current_count,
    )


def needs_comment_refresh(meta: dict) -> bool:
    refresh = meta.get("comments_refresh")
    if not refresh:
        return False
    next_at_str = refresh.get("next_refresh_at")
    if not next_at_str:
        return False
    try:
        next_at = datetime.fromisoformat(next_at_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    return datetime.now(timezone.utc) >= next_at
