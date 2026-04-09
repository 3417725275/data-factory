from data_factory.core.schema import CommentsRefreshState


def _make_state(interval=1, unchanged=0, count=100):
    return CommentsRefreshState(
        current_interval_days=interval,
        consecutive_unchanged=unchanged,
        next_refresh_at="2026-04-08T15:00:00Z",
        last_refresh_at="2026-04-07T15:00:00Z",
        last_comment_count=count,
    )


def test_comments_changed_resets_to_daily():
    from data_factory.core.refresh import compute_next_refresh

    state = _make_state(interval=7, unchanged=3, count=100)
    new_state = compute_next_refresh(current_count=120, refresh_state=state)

    assert new_state.current_interval_days == 1
    assert new_state.consecutive_unchanged == 0
    assert new_state.last_comment_count == 120


def test_first_unchanged_stays_daily():
    from data_factory.core.refresh import compute_next_refresh

    state = _make_state(interval=1, unchanged=0, count=100)
    new_state = compute_next_refresh(current_count=100, refresh_state=state)

    assert new_state.current_interval_days == 1
    assert new_state.consecutive_unchanged == 1


def test_two_unchanged_upgrades_to_3_days():
    from data_factory.core.refresh import compute_next_refresh

    state = _make_state(interval=1, unchanged=1, count=100)
    new_state = compute_next_refresh(current_count=100, refresh_state=state)

    assert new_state.current_interval_days == 3
    assert new_state.consecutive_unchanged == 2


def test_three_unchanged_upgrades_to_7_days():
    from data_factory.core.refresh import compute_next_refresh

    state = _make_state(interval=3, unchanged=2, count=100)
    new_state = compute_next_refresh(current_count=100, refresh_state=state)

    assert new_state.current_interval_days == 7
    assert new_state.consecutive_unchanged == 3


def test_four_unchanged_upgrades_to_14_days():
    from data_factory.core.refresh import compute_next_refresh

    state = _make_state(interval=7, unchanged=3, count=100)
    new_state = compute_next_refresh(current_count=100, refresh_state=state)

    assert new_state.current_interval_days == 14
    assert new_state.consecutive_unchanged == 4


def test_14_days_is_max():
    from data_factory.core.refresh import compute_next_refresh

    state = _make_state(interval=14, unchanged=10, count=100)
    new_state = compute_next_refresh(current_count=100, refresh_state=state)

    assert new_state.current_interval_days == 14
    assert new_state.consecutive_unchanged == 11


def test_reset_from_14_to_daily_on_change():
    from data_factory.core.refresh import compute_next_refresh

    state = _make_state(interval=14, unchanged=10, count=100)
    new_state = compute_next_refresh(current_count=115, refresh_state=state)

    assert new_state.current_interval_days == 1
    assert new_state.consecutive_unchanged == 0
    assert new_state.last_comment_count == 115


def test_needs_comment_refresh_due():
    from data_factory.core.refresh import needs_comment_refresh

    meta = {
        "comments_refresh": {
            "next_refresh_at": "2020-01-01T00:00:00Z",
        }
    }
    assert needs_comment_refresh(meta) is True


def test_needs_comment_refresh_not_due():
    from data_factory.core.refresh import needs_comment_refresh

    meta = {
        "comments_refresh": {
            "next_refresh_at": "2099-12-31T23:59:59Z",
        }
    }
    assert needs_comment_refresh(meta) is False


def test_needs_comment_refresh_no_state():
    from data_factory.core.refresh import needs_comment_refresh

    assert needs_comment_refresh({}) is False
