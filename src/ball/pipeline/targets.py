"""Per-forward-day binary target construction.

For each observation date and each forward day d in 1..Y, the target is 1 iff
the player has an injury event strictly after the observation date and within
d days of it. This is the multi-target structure that produces the day-by-day
risk curve — one model per forward day, never a single collapsed classifier.
"""
import pandas as pd


def injury_dates_by_player(df: pd.DataFrame) -> dict:
    """Map player_id -> sorted list of injury-game dates (is_injured == 1)."""
    return {
        pid: grp.loc[grp["is_injured"] == 1, "game_date"].sort_values().tolist()
        for pid, grp in df.groupby("player_id")
    }


def build_target_row(row_date, injury_dates: list, forward_days: int) -> dict:
    """Targets {d: 0/1} for one observation. Injury on the observation date itself
    does not count (strictly after); an injury exactly d days out does (inclusive)."""
    tgt = {}
    for d in range(1, forward_days + 1):
        end = row_date + pd.Timedelta(days=d)
        tgt[d] = int(any((idt > row_date) and (idt <= end) for idt in injury_dates))
    return tgt
