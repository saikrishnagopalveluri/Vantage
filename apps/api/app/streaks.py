"""The daily streak: how many days in a row someone has opened Vantage. Kept free of the database so
the day-rollover rules can be tested on their own, the same way relevance.py and why.py are."""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class StreakState:
    current_streak: int
    longest_streak: int
    last_active_on: date | None


def apply_touch(state: StreakState, today: date) -> tuple[StreakState, bool]:
    """The state after a touch on `today`.

    Same day as last time: no change (a page can call this every load without inflating the count).
    Exactly one day after last time: the streak continues.
    Anything else (a gap, or the very first touch): the streak restarts at 1.

    Returns the new state and whether it actually changed, so a caller can skip writing to the database
    on a repeat same-day touch.
    """
    if state.last_active_on == today:
        return state, False
    current = state.current_streak + 1 if state.last_active_on == today - timedelta(days=1) else 1
    longest = max(state.longest_streak, current)
    return StreakState(current_streak=current, longest_streak=longest, last_active_on=today), True
