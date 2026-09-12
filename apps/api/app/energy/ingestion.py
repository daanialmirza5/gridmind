"""Energy data ingestion pipeline.

Raw Data -> Validation -> Normalization -> Deduplication -> Unit Conversion
-> Quality Checks -> Energy Ledger

Accepts CSV or JSON rows shaped like:
    timestamp, meter_id, building_id, zone_id, asset_id, energy_kwh (or energy_wh / power_kw),
    temperature_c (or temperature_f), occupancy

Never trusts the incoming file: unknown meters/buildings are rejected, values are
type/range-checked, and nothing overrides normalization rules regardless of what a
row claims about itself (defense against malformed/adversarial import files).
"""

import io
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy.orm import Session

from app.core.errors import GridMindError
from app.domain.structure import Meter

REQUIRED_COLUMNS = {"timestamp", "meter_id"}


@dataclass
class IngestionReport:
    rows_received: int = 0
    rows_valid: int = 0
    rows_rejected_unknown_meter: int = 0
    rows_rejected_invalid: int = 0
    rows_deduplicated: int = 0
    rows_negative_rejected: int = 0
    rows_suspicious_flagged: int = 0
    unit_conversions_applied: int = 0
    errors: list[str] = field(default_factory=list)


def parse_payload(raw_bytes: bytes, content_type: str) -> pd.DataFrame:
    try:
        if "json" in content_type:
            df = pd.read_json(io.BytesIO(raw_bytes))
        else:
            df = pd.read_csv(io.BytesIO(raw_bytes))
    except Exception as exc:
        raise GridMindError("INVALID_PAYLOAD", f"Could not parse uploaded file: {exc}") from exc

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise GridMindError("INVALID_PAYLOAD", f"Missing required columns: {sorted(missing)}")
    return df


def _normalize_units(df: pd.DataFrame, report: IngestionReport) -> pd.DataFrame:
    if "energy_wh" in df.columns and "energy_kwh" not in df.columns:
        df["energy_kwh"] = df["energy_wh"] / 1000.0
        report.unit_conversions_applied += int(df["energy_wh"].notna().sum())
    if "power_w" in df.columns and "power_kw" not in df.columns:
        df["power_kw"] = df["power_w"] / 1000.0
        report.unit_conversions_applied += int(df["power_w"].notna().sum())
    if "temperature_f" in df.columns and "temperature_c" not in df.columns:
        df["temperature_c"] = (df["temperature_f"] - 32) * 5.0 / 9.0
        report.unit_conversions_applied += int(df["temperature_f"].notna().sum())
    if "power_kw" not in df.columns and "energy_kwh" in df.columns:
        df["power_kw"] = df["energy_kwh"]  # hourly interval assumption
    if "energy_kwh" not in df.columns and "power_kw" in df.columns:
        df["energy_kwh"] = df["power_kw"]
    return df


def ingest_dataframe(db: Session, df: pd.DataFrame, source_label: str = "csv_import") -> IngestionReport:
    report = IngestionReport(rows_received=len(df))

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dt.tz_localize(None)
    invalid_ts = df["timestamp"].isna()
    report.rows_rejected_invalid += int(invalid_ts.sum())
    df = df[~invalid_ts]

    df = _normalize_units(df, report)

    if "energy_kwh" not in df.columns:
        raise GridMindError("INVALID_PAYLOAD", "No energy_kwh, energy_wh, or power_kw column found")

    df["energy_kwh"] = pd.to_numeric(df["energy_kwh"], errors="coerce")
    invalid_energy = df["energy_kwh"].isna()
    report.rows_rejected_invalid += int(invalid_energy.sum())
    df = df[~invalid_energy]

    known_meter_ids = {m[0] for m in db.query(Meter.id).all()}
    unknown_meter_mask = ~df["meter_id"].isin(known_meter_ids)
    report.rows_rejected_unknown_meter = int(unknown_meter_mask.sum())
    df = df[~unknown_meter_mask]

    before_dedup = len(df)
    df = df.drop_duplicates(subset=["meter_id", "timestamp"], keep="first")
    report.rows_deduplicated = before_dedup - len(df)

    negative_mask = df["energy_kwh"] < 0
    report.rows_negative_rejected = int(negative_mask.sum())
    df = df[~negative_mask]

    df["data_quality"] = "valid"
    for meter_id, group in df.groupby("meter_id"):
        mean, std = group["energy_kwh"].mean(), group["energy_kwh"].std(ddof=0)
        if std and std > 0:
            z = (group["energy_kwh"] - mean).abs() / std
            suspicious_idx = group.index[z > 5]
            df.loc[suspicious_idx, "data_quality"] = "suspicious"
    report.rows_suspicious_flagged = int((df["data_quality"] == "suspicious").sum())

    meters_meta = {m.id: m for m in db.query(Meter).filter(Meter.id.in_(df["meter_id"].unique())).all()}
    from app.domain.energy import MeterReading  # local import avoids circulars at module load

    inserted = 0
    for _, row in df.iterrows():
        meter = meters_meta.get(row["meter_id"])
        if meter is None:
            continue
        exists = (
            db.query(MeterReading)
            .filter(MeterReading.meter_id == row["meter_id"], MeterReading.timestamp == row["timestamp"])
            .first()
        )
        if exists:
            report.rows_deduplicated += 1
            continue
        db.add(
            MeterReading(
                meter_id=row["meter_id"],
                building_id=meter.building_id,
                zone_id=meter.zone_id,
                asset_id=meter.asset_id,
                timestamp=row["timestamp"],
                energy_kwh=float(row["energy_kwh"]),
                power_kw=float(row.get("power_kw", row["energy_kwh"])),
                temperature_c=row.get("temperature_c"),
                occupancy=row.get("occupancy"),
                operating_state=row.get("operating_state", "unknown") or "unknown",
                data_quality=row["data_quality"],
                source=source_label,
            )
        )
        inserted += 1
    db.commit()

    report.rows_valid = inserted
    return report
