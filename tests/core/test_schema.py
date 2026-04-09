from pathlib import Path


def test_fetch_result_creation():
    from data_factory.core.schema import FetchResult

    r = FetchResult(
        status="ok",
        content_type="video",
        output_dir=Path("/tmp/youtube/abc123"),
        needs_transcribe=True,
    )
    assert r.status == "ok"
    assert r.needs_transcribe is True
    assert r.audio_path is None
    assert r.error is None


def test_fetch_result_error():
    from data_factory.core.schema import FetchResult

    r = FetchResult(
        status="error",
        content_type="video",
        output_dir=Path("/tmp/youtube/abc123"),
        needs_transcribe=False,
        error="Network timeout",
    )
    assert r.status == "error"
    assert r.error == "Network timeout"


def test_comments_refresh_state_creation():
    from data_factory.core.schema import CommentsRefreshState

    s = CommentsRefreshState(
        current_interval_days=1,
        consecutive_unchanged=0,
        next_refresh_at="2026-04-09T15:00:00Z",
        last_refresh_at="2026-04-08T15:00:00Z",
        last_comment_count=320,
    )
    assert s.current_interval_days == 1
    assert s.consecutive_unchanged == 0


def test_comments_refresh_state_to_dict():
    from data_factory.core.schema import CommentsRefreshState

    s = CommentsRefreshState(
        current_interval_days=3,
        consecutive_unchanged=2,
        next_refresh_at="2026-04-14T15:00:00Z",
        last_refresh_at="2026-04-11T15:00:00Z",
        last_comment_count=320,
    )
    d = s.to_dict()
    assert d["current_interval_days"] == 3
    assert d["last_comment_count"] == 320


def test_comments_refresh_state_from_dict():
    from data_factory.core.schema import CommentsRefreshState

    d = {
        "current_interval_days": 7,
        "consecutive_unchanged": 3,
        "next_refresh_at": "2026-04-22T15:00:00Z",
        "last_refresh_at": "2026-04-15T15:00:00Z",
        "last_comment_count": 500,
    }
    s = CommentsRefreshState.from_dict(d)
    assert s.current_interval_days == 7
    assert s.last_comment_count == 500
