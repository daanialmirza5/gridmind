"""Shared operating-schedule lookup used by anomaly detection, waste detection, and optimization."""

import pandas as pd
from sqlalchemy.orm import Session

from app.domain.energy import OperatingSchedule


def load_schedule(db: Session) -> dict[str, dict[int, tuple[int, int] | None]]:
    schedule: dict[str, dict[int, tuple[int, int] | None]] = {}
    for s in db.query(OperatingSchedule).all():
        schedule.setdefault(s.building_id, {})[s.day_of_week] = (
            (s.start_hour, s.end_hour) if s.is_operating_day else None
        )
    return schedule


def is_operating_hour(schedule: dict, building_id: str, ts: pd.Timestamp) -> bool:
    window = schedule.get(building_id, {}).get(ts.dayofweek)
    if window is None:
        return False
    return window[0] <= ts.hour < window[1]


def schedule_end_hour(schedule: dict, building_id: str, ts: pd.Timestamp) -> int | None:
    window = schedule.get(building_id, {}).get(ts.dayofweek)
    return window[1] if window else None
