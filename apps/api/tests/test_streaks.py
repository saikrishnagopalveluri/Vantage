from datetime import date, timedelta

from app.streaks import StreakState, apply_touch
from tests.conftest import as_user

TODAY = date(2026, 9, 25)


def test_a_first_touch_starts_the_streak_at_one():
    state, changed = apply_touch(StreakState(0, 0, None), TODAY)
    assert changed is True
    assert state.current_streak == 1
    assert state.longest_streak == 1
    assert state.last_active_on == TODAY


def test_a_second_touch_the_same_day_is_a_no_op():
    started, _ = apply_touch(StreakState(0, 0, None), TODAY)
    state, changed = apply_touch(started, TODAY)
    assert changed is False
    assert state == started


def test_the_next_day_continues_the_streak():
    yesterday = StreakState(current_streak=5, longest_streak=5, last_active_on=TODAY - timedelta(days=1))
    state, changed = apply_touch(yesterday, TODAY)
    assert changed is True
    assert state.current_streak == 6
    assert state.longest_streak == 6


def test_a_gap_of_more_than_a_day_restarts_the_streak_but_keeps_the_longest():
    lapsed = StreakState(current_streak=12, longest_streak=12, last_active_on=TODAY - timedelta(days=3))
    state, changed = apply_touch(lapsed, TODAY)
    assert changed is True
    assert state.current_streak == 1
    assert state.longest_streak == 12  # the record isn't erased by breaking it


def test_beating_the_longest_streak_updates_it():
    close = StreakState(current_streak=9, longest_streak=10, last_active_on=TODAY - timedelta(days=1))
    state, _ = apply_touch(close, TODAY)
    assert state.current_streak == 10
    assert state.longest_streak == 10


# ---- the router ----------------------------------------------------------------------------------------------------


def test_a_streak_with_no_touches_yet_reads_as_zero(client, world):
    res = client.get("/streaks/u1", headers=as_user("u1"))
    assert res.status_code == 200
    assert res.json() == {"current_streak": 0, "longest_streak": 0, "active_today": False}


def test_touching_starts_the_streak_and_reading_it_back_matches(client, world):
    res = client.post("/streaks/u1/touch", headers=as_user("u1"))
    assert res.status_code == 200
    body = res.json()
    assert body == {"current_streak": 1, "longest_streak": 1, "active_today": True}
    assert client.get("/streaks/u1", headers=as_user("u1")).json() == body


def test_touching_twice_in_one_day_does_not_double_count(client, world):
    client.post("/streaks/u1/touch", headers=as_user("u1"))
    res = client.post("/streaks/u1/touch", headers=as_user("u1"))
    assert res.json()["current_streak"] == 1


def test_a_user_cannot_touch_or_read_someone_elses_streak(client, world):
    assert client.post("/streaks/u2/touch", headers=as_user("u1")).status_code == 403
    assert client.get("/streaks/u2", headers=as_user("u1")).status_code == 403
