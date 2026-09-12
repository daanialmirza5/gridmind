"""Data-quality checks over the energy ledger.

These are read-only diagnostics computed directly from `meter_readings` — they do not
mutate the ledger. Use `app.energy.ingestion` to see checks applied to *new* data before
it is written.
"""

from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class DataQualityReport:
    scope: str
    total_readings: int
    valid_readings: int
    missing_intervals: int
    duplicate_readings: int
    suspicious_readings: int
    negative_readings: int
    stale_sensor_readings: int


def _load_readings(db: Session, building_id: str | None) -> pd.DataFrame:
    query = "SELECT meter_id, timestamp, energy_kwh, data_quality FROM meter_readings"
    params = {}
    if building_id:
        query += " WHERE building_id = :building_id"
        params["building_id"] = building_id
    rows = db.execute(text(query), params).fetchall()
    return pd.DataFrame(rows, columns=["meter_id", "timestamp", "energy_kwh", "data_quality"])


def compute_data_quality_report(db: Session, building_id: str | None = None) -> DataQualityReport:
    df = _load_readings(db, building_id)
    if df.empty:
        return DataQualityReport(building_id or "all", 0, 0, 0, 0, 0, 0, 0)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    negative = int((df["energy_kwh"] < 0).sum())

    missing_intervals = 0
    stale = 0
    for meter_id, g in df.groupby("meter_id"):
        g = g.sort_values("timestamp")
        expected = int((g["timestamp"].max() - g["timestamp"].min()) / pd.Timedelta(hours=1)) + 1
        missing_intervals += max(expected - len(g), 0)
        # stale sensor: 5+ consecutive identical readings
        same_as_prev = g["energy_kwh"].diff().abs() < 1e-9
        run_length = 0
        for is_same in same_as_prev.fillna(False):
            run_length = run_length + 1 if is_same else 0
            if run_length == 5:  # count once per stale run, at the point it's confirmed
                stale += 5
            elif run_length > 5:
                stale += 1

    suspicious_mask = df["data_quality"] == "suspicious"
    duplicate_mask = df["data_quality"] == "duplicate"

    return DataQualityReport(
        scope=building_id or "all",
        total_readings=len(df),
        valid_readings=int((df["data_quality"] == "valid").sum()),
        missing_intervals=missing_intervals,
        duplicate_readings=int(duplicate_mask.sum()),
        suspicious_readings=int(suspicious_mask.sum()),
        negative_readings=negative,
        stale_sensor_readings=stale,
    )
