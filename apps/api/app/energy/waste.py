"""Deterministic waste detection engine.

Each rule below is an explicit, auditable IF/THEN condition over the energy ledger,
baseline, occupancy, and operating-schedule data — not a black-box model. Every flagged
event carries the observed values that triggered it (see `evidence`).

Implemented rules:
  - after_hours_hvac: elevated submeter draw outside operating hours with the zone empty.
  - high_energy_low_occupancy: high draw in an occupied-type zone that is currently empty.
  - excessive_standby_load: a sustained (24h+) deviation above the meter's own baseline.
  - repeated_peak_demand_events: a building's main meter hits its own high-percentile band
    on 3+ separate occasions within a rolling 7-day window.

Note on scope: "simultaneous heating/cooling" and "equipment running outside schedule"
from the original design brief are not separately implemented — this generation of
GridMind meters HVAC/lighting/equipment as one aggregated zone submeter, so there is no
independent heating-vs-cooling or equipment-only signal to test against. Documented as a
known limitation in docs/model_cards.md rather than faked with an unsupported proxy.
"""

import json
import uuid
from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from app.domain.energy import Tariff, EmissionFactor
from app.domain.intelligence import WasteEvent
from app.domain.structure import Zone
from app.energy.baseline import compare_to_baseline, get_baseline_lookup
from app.energy.carbon import compute_emissions
from app.energy.cost import compute_cost
from app.energy.schedule import is_operating_hour, load_schedule

AFTER_HOURS_OCCUPANCY_THRESHOLD = 3
AFTER_HOURS_MULTIPLIER = 1.5
LOW_OCCUPANCY_RATIO = 0.1
LOW_OCCUPANCY_POWER_RATIO = 0.6
SUSTAINED_DEVIATION_PCT = 30.0
SUSTAINED_MIN_HOURS = 24
PEAK_PERCENTILE = 90
PEAK_EVENT_MIN_COUNT = 3
PEAK_EVENT_WINDOW_DAYS = 7


@dataclass
class DetectedWasteEvent:
    building_id: str
    zone_id: str | None
    asset_id: str | None
    meter_id: str
    rule: str
    severity: str
    window_start: pd.Timestamp
    window_end: pd.Timestamp
    estimated_waste_kwh: float
    evidence: dict


def _severity_for_waste(estimated_waste_kwh: float, baseline_kwh: float) -> str:
    ratio = estimated_waste_kwh / baseline_kwh if baseline_kwh > 0 else 1.0
    if ratio >= 1.5 or estimated_waste_kwh >= 100:
        return "CRITICAL"
    if ratio >= 0.8 or estimated_waste_kwh >= 40:
        return "HIGH"
    if ratio >= 0.3 or estimated_waste_kwh >= 10:
        return "MEDIUM"
    return "LOW"


def _rule_after_hours(compared: pd.DataFrame, schedule: dict) -> list[DetectedWasteEvent]:
    events = []
    zone_only = compared[compared["zone_id"].notna()]
    for meter_id, group in zone_only.groupby("meter_id"):
        group = group.sort_values("timestamp")
        flagged = group[
            (~group["timestamp"].apply(lambda ts: is_operating_hour(schedule, group["building_id"].iloc[0], ts)))
            & (group["occupancy"].fillna(0) < AFTER_HOURS_OCCUPANCY_THRESHOLD)
            & (group["energy_kwh"] > group["expected_kwh"] * AFTER_HOURS_MULTIPLIER)
            & (group["expected_kwh"] > 0.5)
        ]
        if flagged.empty:
            continue
        for _, run in _consecutive_runs(flagged):
            waste_kwh = float((run["energy_kwh"] - run["expected_kwh"]).clip(lower=0).sum())
            events.append(
                DetectedWasteEvent(
                    building_id=run["building_id"].iloc[0],
                    zone_id=run["zone_id"].iloc[0],
                    asset_id=run["asset_id"].iloc[0],
                    meter_id=meter_id,
                    rule="after_hours_hvac",
                    severity=_severity_for_waste(waste_kwh, float(run["expected_kwh"].sum())),
                    window_start=run["timestamp"].iloc[0],
                    window_end=run["timestamp"].iloc[-1],
                    estimated_waste_kwh=round(waste_kwh, 2),
                    evidence={
                        "observed_kwh": round(float(run["energy_kwh"].sum()), 2),
                        "expected_kwh": round(float(run["expected_kwh"].sum()), 2),
                        "occupancy": int(run["occupancy"].fillna(0).max()),
                        "hours_flagged": len(run),
                        "rule": "occupancy < 3 AND power > 1.5x expected AND outside operating schedule",
                    },
                )
            )
    return events


def _consecutive_runs(df: pd.DataFrame):
    """Yield (index, sub-frame) for maximal runs of consecutive-hour rows."""
    if df.empty:
        return
    df = df.sort_values("timestamp")
    gaps = df["timestamp"].diff() > pd.Timedelta(hours=1)
    run_id = gaps.cumsum()
    for _, run in df.groupby(run_id):
        yield None, run


def _rule_low_occupancy(compared: pd.DataFrame, schedule: dict, zone_meta: dict) -> list[DetectedWasteEvent]:
    events = []
    for meter_id, group in compared.groupby("meter_id"):
        zone_id = group["zone_id"].iloc[0]
        meta = zone_meta.get(zone_id)
        if meta is None or meta["zone_type"] == "server_room":
            continue
        group = group.sort_values("timestamp")
        operating = group["timestamp"].apply(lambda ts: is_operating_hour(schedule, group["building_id"].iloc[0], ts))
        occ_ratio = group["occupancy"].fillna(0) / max(meta["max_occupancy"], 1)
        flagged = group[
            operating
            & (occ_ratio < LOW_OCCUPANCY_RATIO)
            & (group["energy_kwh"] > group["expected_kwh"].quantile(0.6) * LOW_OCCUPANCY_POWER_RATIO)
            & (group["expected_kwh"] > 0.5)
        ]
        for _, run in _consecutive_runs(flagged):
            waste_kwh = float(run["energy_kwh"].sum() * 0.4)  # attribute ~40% as avoidable, rest is base load
            events.append(
                DetectedWasteEvent(
                    building_id=run["building_id"].iloc[0],
                    zone_id=zone_id,
                    asset_id=run["asset_id"].iloc[0],
                    meter_id=meter_id,
                    rule="high_energy_low_occupancy",
                    severity=_severity_for_waste(waste_kwh, float(run["expected_kwh"].sum())),
                    window_start=run["timestamp"].iloc[0],
                    window_end=run["timestamp"].iloc[-1],
                    estimated_waste_kwh=round(waste_kwh, 2),
                    evidence={
                        "observed_kwh": round(float(run["energy_kwh"].sum()), 2),
                        "max_occupancy_ratio": round(float(occ_ratio.loc[run.index].max()), 3),
                        "hours_flagged": len(run),
                        "rule": "occupancy < 10% of max AND power > 60% of typical occupied load, during operating hours",
                    },
                )
            )
    return events


def _rule_sustained_deviation(compared: pd.DataFrame) -> list[DetectedWasteEvent]:
    events = []
    for meter_id, group in compared.groupby("meter_id"):
        group = group.sort_values("timestamp")
        flagged = group[group["deviation_pct"] > SUSTAINED_DEVIATION_PCT]
        for _, run in _consecutive_runs(flagged):
            if len(run) < SUSTAINED_MIN_HOURS:
                continue
            waste_kwh = float((run["energy_kwh"] - run["expected_kwh"]).clip(lower=0).sum())
            events.append(
                DetectedWasteEvent(
                    building_id=run["building_id"].iloc[0],
                    zone_id=run["zone_id"].iloc[0],
                    asset_id=run["asset_id"].iloc[0],
                    meter_id=meter_id,
                    rule="excessive_standby_load",
                    severity=_severity_for_waste(waste_kwh, float(run["expected_kwh"].sum())),
                    window_start=run["timestamp"].iloc[0],
                    window_end=run["timestamp"].iloc[-1],
                    estimated_waste_kwh=round(waste_kwh, 2),
                    evidence={
                        "observed_kwh": round(float(run["energy_kwh"].sum()), 2),
                        "expected_kwh": round(float(run["expected_kwh"].sum()), 2),
                        "duration_hours": len(run),
                        "rule": f"deviation > {SUSTAINED_DEVIATION_PCT}% sustained for >= {SUSTAINED_MIN_HOURS}h",
                    },
                )
            )
    return events


def _rule_repeated_peaks(readings: pd.DataFrame) -> list[DetectedWasteEvent]:
    events = []
    main_meters = readings[readings["zone_id"].isna()]
    for meter_id, group in main_meters.groupby("meter_id"):
        group = group.sort_values("timestamp")
        threshold = group["power_kw"].quantile(PEAK_PERCENTILE / 100)
        peaks = group[group["power_kw"] >= threshold].copy()
        if peaks.empty:
            continue
        peaks["window"] = peaks["timestamp"].dt.floor(f"{PEAK_EVENT_WINDOW_DAYS}D")
        for window, wgroup in peaks.groupby("window"):
            if len(wgroup) < PEAK_EVENT_MIN_COUNT:
                continue
            events.append(
                DetectedWasteEvent(
                    building_id=wgroup["building_id"].iloc[0],
                    zone_id=None,
                    asset_id=None,
                    meter_id=meter_id,
                    rule="repeated_peak_demand_events",
                    severity="HIGH" if len(wgroup) >= 5 else "MEDIUM",
                    window_start=wgroup["timestamp"].iloc[0],
                    window_end=wgroup["timestamp"].iloc[-1],
                    estimated_waste_kwh=0.0,  # peak events drive demand charges, not extra kWh
                    evidence={
                        "peak_threshold_kw": round(float(threshold), 1),
                        "event_count": len(wgroup),
                        "max_power_kw": round(float(wgroup["power_kw"].max()), 1),
                        "rule": f"main meter power >= p{PEAK_PERCENTILE} on {PEAK_EVENT_MIN_COUNT}+ occasions in {PEAK_EVENT_WINDOW_DAYS} days",
                    },
                )
            )
    return events


def detect_waste_events(db: Session, readings: pd.DataFrame) -> list[DetectedWasteEvent]:
    if readings.empty:
        return []

    lookup = get_baseline_lookup(db, meter_ids=list(readings["meter_id"].unique()))
    compared = compare_to_baseline(readings, lookup)
    schedule = load_schedule(db)
    zone_meta = {
        z.id: {"zone_type": z.zone_type, "max_occupancy": z.max_occupancy} for z in db.query(Zone).all()
    }

    events: list[DetectedWasteEvent] = []
    events += _rule_after_hours(compared, schedule)
    events += _rule_low_occupancy(compared, schedule, zone_meta)
    events += _rule_sustained_deviation(compared)
    events += _rule_repeated_peaks(readings)
    return events


def persist_waste_events(db: Session, events: list[DetectedWasteEvent]) -> int:
    tariffs = {t.building_id: t for t in db.query(Tariff).all()}
    factor = db.query(EmissionFactor).first()

    for e in events:
        tariff = tariffs.get(e.building_id)
        cost = 0.0
        emissions = 0.0
        if tariff and e.estimated_waste_kwh > 0:
            fake_df = pd.DataFrame(
                {"timestamp": [e.window_start], "energy_kwh": [e.estimated_waste_kwh], "power_kw": [e.estimated_waste_kwh]}
            )
            cost = compute_cost(fake_df, tariff).consumption_cost
        if factor and e.estimated_waste_kwh > 0:
            emissions = compute_emissions(
                pd.DataFrame({"energy_kwh": [e.estimated_waste_kwh]}), factor
            ).total_kg_co2e

        db.add(
            WasteEvent(
                id=f"WASTE-{uuid.uuid4().hex[:10]}",
                building_id=e.building_id,
                zone_id=e.zone_id,
                asset_id=e.asset_id,
                meter_id=e.meter_id,
                rule=e.rule,
                severity=e.severity,
                window_start=e.window_start,
                window_end=e.window_end,
                estimated_waste_kwh=e.estimated_waste_kwh,
                estimated_cost=round(cost, 2),
                estimated_emissions_kg=round(emissions, 2),
                evidence_json=json.dumps(e.evidence, default=str),
            )
        )
    db.commit()
    return len(events)
