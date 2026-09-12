"""Baseline energy model: expected consumption under normal conditions.

Method: for each meter, bucket historical hourly readings by (day_of_week, hour_of_day)
and take the mean/std of energy_kwh in that bucket. This captures weekday/weekend and
time-of-day patterns without needing external weather/occupancy regressors, while still
staying transparent and auditable (168 buckets/week per meter). Documented as a
methodology limitation: it does not yet condition on outdoor temperature directly (that
signal is folded in implicitly since bucket means average over many days at varying
temperatures).
"""

from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from app.domain.energy import EnergyBaseline


@dataclass
class BaselineComparison:
    meter_id: str
    timestamp: pd.Timestamp
    expected_kwh: float
    actual_kwh: float
    deviation_pct: float
    std_dev_kwh: float


def compute_and_store_baselines(db: Session, readings: pd.DataFrame) -> int:
    """Recompute (day_of_week, hour_of_day) baseline buckets for every meter in `readings`."""
    if readings.empty:
        return 0

    df = readings.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["hour_of_day"] = df["timestamp"].dt.hour

    grouped = df.groupby(["meter_id", "day_of_week", "hour_of_day"])["energy_kwh"].agg(["mean", "std", "count"])
    grouped = grouped.reset_index()

    db.query(EnergyBaseline).delete()

    rows = []
    for _, r in grouped.iterrows():
        std = r["std"] if pd.notna(r["std"]) else 0.0
        rows.append(
            EnergyBaseline(
                meter_id=r["meter_id"],
                day_of_week=int(r["day_of_week"]),
                hour_of_day=int(r["hour_of_day"]),
                expected_kwh=float(r["mean"]),
                std_dev_kwh=float(std),
                sample_count=int(r["count"]),
            )
        )
    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)


def get_baseline_lookup(db: Session, meter_ids: list[str] | None = None) -> dict[tuple[str, int, int], tuple[float, float]]:
    query = db.query(EnergyBaseline)
    if meter_ids:
        query = query.filter(EnergyBaseline.meter_id.in_(meter_ids))
    lookup = {}
    for b in query.all():
        lookup[(b.meter_id, b.day_of_week, b.hour_of_day)] = (b.expected_kwh, b.std_dev_kwh)
    return lookup


def compare_to_baseline(readings: pd.DataFrame, baseline_lookup: dict) -> pd.DataFrame:
    df = readings.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["hour_of_day"] = df["timestamp"].dt.hour

    def lookup_expected(row):
        key = (row["meter_id"], row["day_of_week"], row["hour_of_day"])
        return baseline_lookup.get(key, (row["energy_kwh"], 0.0))

    expected_std = df.apply(lookup_expected, axis=1, result_type="expand")
    df["expected_kwh"] = expected_std[0]
    df["std_dev_kwh"] = expected_std[1]
    df["deviation_pct"] = (
        (df["energy_kwh"] - df["expected_kwh"]) / df["expected_kwh"].replace(0, pd.NA)
    ) * 100
    df["deviation_pct"] = df["deviation_pct"].fillna(0.0)
    return df
