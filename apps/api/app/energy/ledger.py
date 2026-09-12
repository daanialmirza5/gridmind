"""Query layer over the normalized energy ledger (meter_readings)."""

from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


def query_readings(
    db: Session,
    building_id: str | None = None,
    zone_id: str | None = None,
    meter_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> pd.DataFrame:
    clauses = []
    params: dict = {}
    if building_id:
        clauses.append("building_id = :building_id")
        params["building_id"] = building_id
    if zone_id:
        clauses.append("zone_id = :zone_id")
        params["zone_id"] = zone_id
    if meter_id:
        clauses.append("meter_id = :meter_id")
        params["meter_id"] = meter_id
    if start:
        clauses.append("timestamp >= :start")
        params["start"] = start
    if end:
        clauses.append("timestamp < :end")
        params["end"] = end

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT meter_id, building_id, zone_id, asset_id, timestamp, energy_kwh, power_kw,
               temperature_c, occupancy, operating_state, data_quality
        FROM meter_readings
        {where}
        ORDER BY timestamp
    """
    rows = db.execute(text(query), params).fetchall()
    df = pd.DataFrame(
        rows,
        columns=[
            "meter_id", "building_id", "zone_id", "asset_id", "timestamp", "energy_kwh",
            "power_kw", "temperature_c", "occupancy", "operating_state", "data_quality",
        ],
    )
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def latest_timestamp(db: Session, building_id: str | None = None) -> datetime | None:
    df = query_readings(db, building_id=building_id)
    if df.empty:
        return None
    return df["timestamp"].max().to_pydatetime()


def dataset_bounds(db: Session) -> tuple[datetime | None, datetime | None]:
    rows = db.execute(text("SELECT MIN(timestamp), MAX(timestamp) FROM meter_readings")).fetchone()
    if not rows or rows[0] is None:
        return None, None
    return pd.to_datetime(rows[0]).to_pydatetime(), pd.to_datetime(rows[1]).to_pydatetime()


def kpi_summary(db: Session, building_id: str | None = None) -> dict:
    """Core KPI tile values, all computed from actual ledger data ending at the dataset's latest timestamp."""
    _, latest = dataset_bounds(db)
    if latest is None:
        return {}

    today_start = latest.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = latest.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    window_start = latest - timedelta(days=30)

    main_only_clause = "AND zone_id IS NULL" if building_id else ""
    params = {
        "today_start": today_start,
        "latest": latest,
        "month_start": month_start,
        "window_start": window_start,
    }
    if building_id:
        params["building_id"] = building_id
    building_clause = "AND building_id = :building_id" if building_id else ""

    def scalar(query: str) -> float:
        result = db.execute(text(query), params).scalar()
        return float(result) if result is not None else 0.0

    today_energy = scalar(
        f"""SELECT SUM(energy_kwh) FROM meter_readings
            WHERE timestamp >= :today_start AND timestamp <= :latest {building_clause} {main_only_clause}"""
    )
    month_energy = scalar(
        f"""SELECT SUM(energy_kwh) FROM meter_readings
            WHERE timestamp >= :month_start AND timestamp <= :latest {building_clause} {main_only_clause}"""
    )
    current_demand = scalar(
        f"""SELECT power_kw FROM meter_readings
            WHERE timestamp = :latest {building_clause} {main_only_clause} LIMIT 1"""
    )
    peak_demand_30d = scalar(
        f"""SELECT MAX(power_kw) FROM meter_readings
            WHERE timestamp >= :window_start AND timestamp <= :latest {building_clause} {main_only_clause}"""
    )

    return {
        "as_of": latest,
        "today_energy_kwh": round(today_energy, 1),
        "month_energy_kwh": round(month_energy, 1),
        "current_demand_kw": round(current_demand, 1),
        "peak_demand_kw": round(peak_demand_30d, 1),
    }
