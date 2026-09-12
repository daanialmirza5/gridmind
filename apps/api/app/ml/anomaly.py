"""Energy anomaly detection.

Two complementary, non-parametric statistical methods are combined rather than a single
arbitrary threshold:

1. Robust baseline z-score: (actual - expected_for_this_hour_of_week) / std_dev_for_that_bucket,
   using the EnergyBaseline buckets (see app.energy.baseline).
2. IQR check: flags a reading if it falls outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR] of that
   meter's overall distribution, which catches anomalies even where the baseline bucket
   itself is degenerate (near-zero std, e.g. an always-off overnight bucket).

A reading is flagged only when BOTH conditions agree the value is unusual, which keeps
false positives down relative to either method alone.
"""

import json
import uuid
from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from app.domain.intelligence import Anomaly
from app.energy.baseline import compare_to_baseline, get_baseline_lookup
from app.energy.schedule import is_operating_hour, load_schedule

Z_SCORE_THRESHOLD = 2.2
MIN_DEVIATION_PCT = 15.0


@dataclass
class DetectedAnomaly:
    meter_id: str
    building_id: str
    zone_id: str | None
    timestamp: pd.Timestamp
    expected_kwh: float
    actual_kwh: float
    deviation_pct: float
    z_score: float
    severity: str
    probable_cause: str
    evidence: dict


def _severity(z_score: float) -> str:
    az = abs(z_score)
    if az >= 5:
        return "CRITICAL"
    if az >= 3.5:
        return "HIGH"
    if az >= 2.6:
        return "MEDIUM"
    return "LOW"


def detect_anomalies(db: Session, readings: pd.DataFrame) -> list[DetectedAnomaly]:
    if readings.empty:
        return []

    lookup = get_baseline_lookup(db, meter_ids=list(readings["meter_id"].unique()))
    compared = compare_to_baseline(readings, lookup)
    schedule = load_schedule(db)

    results: list[DetectedAnomaly] = []
    for meter_id, group in compared.groupby("meter_id"):
        series = group["energy_kwh"]
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower_bound, upper_bound = q1 - 1.5 * iqr, q3 + 1.5 * iqr

        for _, row in group.iterrows():
            std = row["std_dev_kwh"] if row["std_dev_kwh"] > 1e-6 else max(row["expected_kwh"] * 0.1, 0.05)
            z = (row["energy_kwh"] - row["expected_kwh"]) / std
            iqr_flag = row["energy_kwh"] < lower_bound or row["energy_kwh"] > upper_bound

            if abs(z) < Z_SCORE_THRESHOLD or not iqr_flag or abs(row["deviation_pct"]) < MIN_DEVIATION_PCT:
                continue

            operating = is_operating_hour(schedule, row["building_id"], row["timestamp"])
            if row["deviation_pct"] > 0 and not operating:
                cause = "Abnormal after-hours consumption"
            elif row["deviation_pct"] > 0:
                cause = "Consumption significantly above expected pattern for this hour"
            else:
                cause = "Consumption significantly below expected pattern (possible outage or schedule change)"

            results.append(
                DetectedAnomaly(
                    meter_id=meter_id,
                    building_id=row["building_id"],
                    zone_id=row["zone_id"],
                    timestamp=row["timestamp"],
                    expected_kwh=round(float(row["expected_kwh"]), 2),
                    actual_kwh=round(float(row["energy_kwh"]), 2),
                    deviation_pct=round(float(row["deviation_pct"]), 1),
                    z_score=round(float(z), 2),
                    severity=_severity(z),
                    probable_cause=cause,
                    evidence={
                        "meter_id": meter_id,
                        "timestamp": row["timestamp"].isoformat(),
                        "expected_kwh": round(float(row["expected_kwh"]), 2),
                        "actual_kwh": round(float(row["energy_kwh"]), 2),
                        "std_dev_kwh": round(float(std), 2),
                        "z_score": round(float(z), 2),
                        "iqr_bounds": [round(float(lower_bound), 2), round(float(upper_bound), 2)],
                        "operating_hour": operating,
                        "detection_methods": ["rolling_zscore", "iqr"],
                    },
                )
            )
    return results


def persist_anomalies(db: Session, anomalies: list[DetectedAnomaly]) -> int:
    for a in anomalies:
        db.add(
            Anomaly(
                id=f"ANOM-{uuid.uuid4().hex[:10]}",
                meter_id=a.meter_id,
                building_id=a.building_id,
                timestamp=a.timestamp,
                expected_kwh=a.expected_kwh,
                actual_kwh=a.actual_kwh,
                deviation_pct=a.deviation_pct,
                severity=a.severity,
                detection_method="rolling_zscore+iqr",
                probable_cause=a.probable_cause,
                evidence_json=json.dumps(a.evidence, default=str),
            )
        )
    db.commit()
    return len(anomalies)
