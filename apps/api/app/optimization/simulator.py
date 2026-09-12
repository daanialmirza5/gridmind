"""What-if scenario simulator.

GridMind's energy ledger stores one aggregated power reading per meter (zone submeters
mix HVAC + lighting + equipment; see docs/model_cards.md). Rather than pretend to
re-simulate building physics we don't have separate telemetry for, each lever below
applies a documented, transparent adjustment formula directly to historical readings.
This is explicitly a demo-grade approximation, not a physics engine — every constant is
named and justified so the methodology is auditable.

Levers (all optional, default = no change):
  hvac_setpoint_delta_c: raise(+)/lower(-) the cooling setpoint. Adjusts the
      temperature-sensitive share of operating-hour load using the same thermal-load
      formula the synthetic generator itself uses (see seed/timeseries.py).
  after_hours_cutback_hours: number of hours immediately after the daily schedule ends
      during which HVAC is pushed most of the way to the meter's own deep-standby level.
  lighting_reduction_pct: flat dimming applied to the estimated lighting share of
      operating-hour load in non-server-room zones.
  peak_shift_kw: average kW shifted out of the tariff's peak window into off-peak hours
      of the same day (energy-neutral; targets cost and demand, not total kWh).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.energy.schedule import is_operating_hour, schedule_end_hour

HVAC_SETPOINT_C = 22.0
HVAC_THERMAL_SENSITIVITY = 0.35  # share of operating-hour load treated as setpoint-sensitive HVAC
AFTER_HOURS_CUTBACK_EFFECTIVENESS = 0.80  # fraction of the gap to deep-standby that is closed
LIGHTING_SHARE_OF_NON_HVAC = 0.50  # documented assumption for non-server-room zones


@dataclass
class ScenarioLevers:
    hvac_setpoint_delta_c: float = 0.0
    after_hours_cutback_hours: int = 0
    lighting_reduction_pct: float = 0.0
    peak_shift_kw: float = 0.0

    def as_dict(self) -> dict:
        return {
            "hvac_setpoint_delta_c": self.hvac_setpoint_delta_c,
            "after_hours_cutback_hours": self.after_hours_cutback_hours,
            "lighting_reduction_pct": self.lighting_reduction_pct,
            "peak_shift_kw": self.peak_shift_kw,
        }


PRESETS: dict[str, ScenarioLevers] = {
    "conservative": ScenarioLevers(hvac_setpoint_delta_c=1.0, after_hours_cutback_hours=1, lighting_reduction_pct=10, peak_shift_kw=0),
    "balanced": ScenarioLevers(hvac_setpoint_delta_c=2.0, after_hours_cutback_hours=2, lighting_reduction_pct=20, peak_shift_kw=5),
    "aggressive": ScenarioLevers(hvac_setpoint_delta_c=3.0, after_hours_cutback_hours=3, lighting_reduction_pct=35, peak_shift_kw=15),
}


def _thermal_load(temp_c: np.ndarray, setpoint: float) -> np.ndarray:
    return np.clip(np.abs(temp_c - setpoint) / 15.0, 0, 1.6)


def apply_setpoint_lever(df: pd.DataFrame, delta_c: float, operating_mask: pd.Series, rated_kw: pd.Series) -> pd.Series:
    """Additive adjustment (not a ratio) so a near-zero baseline thermal load can never
    blow up into a huge multiplier: delta_power = (new_load - old_load) * rated_kw * weight,
    using the same thermal-load formula and active/standby weighting as the synthetic
    generator itself (see seed/timeseries.py::_hvac_power)."""
    if delta_c == 0:
        return df["energy_kwh"]
    old_load = _thermal_load(df["temperature_c"].to_numpy(dtype=float), HVAC_SETPOINT_C)
    new_load = _thermal_load(df["temperature_c"].to_numpy(dtype=float), HVAC_SETPOINT_C + delta_c)
    weight = np.where(operating_mask, 0.85, 0.05)
    delta_power = (new_load - old_load) * rated_kw.to_numpy(dtype=float) * weight * HVAC_THERMAL_SENSITIVITY
    adjusted = df["energy_kwh"].to_numpy(dtype=float) + delta_power
    return pd.Series(np.clip(adjusted, 0, None), index=df.index)


def apply_after_hours_cutback(df: pd.DataFrame, hours: int, schedule: dict, building_id: str) -> pd.Series:
    if hours <= 0:
        return df["energy_kwh"]
    energy = df["energy_kwh"].to_numpy(dtype=float).copy()
    non_operating = ~df["timestamp"].apply(lambda ts: is_operating_hour(schedule, building_id, ts)).to_numpy()
    deep_standby = float(df.loc[non_operating, "energy_kwh"].quantile(0.10)) if non_operating.any() else 0.0

    hours_since_close = df["timestamp"].apply(
        lambda ts: _hours_since_schedule_end(ts, schedule, building_id)
    ).to_numpy()
    in_cutback_window = non_operating & (hours_since_close >= 0) & (hours_since_close < hours)

    gap = energy[in_cutback_window] - deep_standby
    energy[in_cutback_window] = energy[in_cutback_window] - AFTER_HOURS_CUTBACK_EFFECTIVENESS * np.clip(gap, 0, None)
    return pd.Series(np.clip(energy, 0, None), index=df.index)


def _hours_since_schedule_end(ts: pd.Timestamp, schedule: dict, building_id: str) -> float:
    end_hour = schedule_end_hour(schedule, building_id, ts)
    if end_hour is None:
        return -1.0
    if ts.hour < end_hour:
        return -1.0
    return float(ts.hour - end_hour)


def apply_lighting_reduction(df: pd.DataFrame, reduction_pct: float, operating_mask: pd.Series, zone_type: str | None) -> pd.Series:
    if reduction_pct <= 0 or zone_type in (None, "server_room"):
        return df["energy_kwh"]
    non_hvac_share = 1 - HVAC_THERMAL_SENSITIVITY
    factor = 1 - (reduction_pct / 100.0) * non_hvac_share * LIGHTING_SHARE_OF_NON_HVAC
    energy = df["energy_kwh"].to_numpy(dtype=float)
    adjusted = np.where(operating_mask, energy * factor, energy)
    return pd.Series(adjusted, index=df.index)


def apply_peak_shift(df: pd.DataFrame, shift_kw: float, tariff) -> pd.Series:
    if shift_kw <= 0 or tariff.tariff_type != "time_of_use":
        return df["energy_kwh"]
    energy = df["energy_kwh"].to_numpy(dtype=float).copy()
    ts = df["timestamp"]
    is_peak = (ts.dt.hour >= tariff.peak_start_hour) & (ts.dt.hour < tariff.peak_end_hour)
    df_local = df.assign(_date=ts.dt.date, _is_peak=is_peak)

    for (_meter_id, _date), day_group in df_local.groupby(["meter_id", "_date"]):
        peak_idx = day_group.index[day_group["_is_peak"]]
        off_peak_idx = day_group.index[~day_group["_is_peak"]]
        if len(peak_idx) == 0 or len(off_peak_idx) == 0:
            continue
        removable = np.minimum(shift_kw, energy[peak_idx])
        total_shifted = float(removable.sum())
        energy[peak_idx] -= removable
        energy[off_peak_idx] += total_shifted / len(off_peak_idx)
    return pd.Series(np.clip(energy, 0, None), index=df.index)


@dataclass
class ScenarioMetrics:
    baseline_energy_kwh: float
    scenario_energy_kwh: float
    baseline_cost: float
    scenario_cost: float
    baseline_peak_kw: float
    scenario_peak_kw: float
    baseline_emissions_kg: float
    scenario_emissions_kg: float
    energy_change_pct: float
    cost_change_pct: float
    peak_change_pct: float
    emissions_change_pct: float


def _pct_change(baseline: float, scenario: float) -> float:
    if baseline == 0:
        return 0.0
    return round(((scenario - baseline) / baseline) * 100, 2)


OBJECTIVE_WEIGHTS = {
    "cost": {"cost": 0.70, "energy": 0.10, "emissions": 0.10, "peak": 0.10},
    "energy": {"cost": 0.10, "energy": 0.70, "emissions": 0.10, "peak": 0.10},
    "emissions": {"cost": 0.10, "energy": 0.10, "emissions": 0.70, "peak": 0.10},
    "peak": {"cost": 0.10, "energy": 0.10, "emissions": 0.10, "peak": 0.70},
    "balanced": {"cost": 0.45, "energy": 0.30, "emissions": 0.15, "peak": 0.10},
}


def objective_score(metrics: ScenarioMetrics, objective: str) -> float:
    """Lower is better. Weighted sum of % changes (negative % change = improvement)."""
    weights = OBJECTIVE_WEIGHTS.get(objective, OBJECTIVE_WEIGHTS["balanced"])
    return round(
        weights["cost"] * metrics.cost_change_pct
        + weights["energy"] * metrics.energy_change_pct
        + weights["emissions"] * metrics.emissions_change_pct
        + weights["peak"] * metrics.peak_change_pct,
        3,
    )
