"""Synthetic hourly energy time-series generator with injected, ground-truth-tracked anomalies.

Everything here is deterministic given a fixed random seed, so the dataset (and the
ground-truth anomaly list used for evaluation) is fully reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from seed.structure import BuildingSpec

SCHEDULES = {
    # kind -> {day_of_week(0=Mon..6=Sun): (start_hour, end_hour) or None if closed}
    "office": {0: (8, 18), 1: (8, 18), 2: (8, 18), 3: (8, 18), 4: (8, 18), 5: None, 6: None},
    "mixed": {0: (7, 19), 1: (7, 19), 2: (7, 19), 3: (7, 19), 4: (7, 19), 5: None, 6: None},
    "retail": {0: (9, 20), 1: (9, 20), 2: (9, 20), 3: (9, 20), 4: (9, 20), 5: (9, 20), 6: (10, 16)},
}

HVAC_SETPOINT_C = 22.0


@dataclass
class GroundTruthAnomaly:
    id: str
    meter_id: str
    building_id: str
    zone_id: str | None
    anomaly_type: str
    start: pd.Timestamp
    end: pd.Timestamp
    description: str


def _operating_mask(index: pd.DatetimeIndex, kind: str) -> np.ndarray:
    sched = SCHEDULES[kind]
    mask = np.zeros(len(index), dtype=bool)
    for i, ts in enumerate(index):
        window = sched[ts.dayofweek]
        if window is None:
            continue
        start, end = window
        if start <= ts.hour < end:
            mask[i] = True
    return mask


def _weather_series(index: pd.DatetimeIndex, rng: np.random.Generator) -> np.ndarray:
    doy = index.dayofyear.to_numpy()
    hour = index.hour.to_numpy()
    seasonal = 18.0 + 10.0 * np.cos(2 * np.pi * (doy - 200) / 365.0)
    daily = 5.0 * np.sin(2 * np.pi * (hour - 9) / 24.0)
    noise = rng.normal(0, 1.2, size=len(index))
    return seasonal + daily + noise


def _occupancy_fraction(hour: np.ndarray, start: int, end: int) -> np.ndarray:
    frac = np.zeros_like(hour, dtype=float)
    in_window = (hour >= start) & (hour < end)
    rel = (hour - start).astype(float)
    ramp_up = np.clip(rel, 0, 1)
    ramp_down = np.clip((end - hour).astype(float), 0, 1)
    plateau = np.minimum(ramp_up, ramp_down)
    frac[in_window] = np.clip(plateau[in_window], 0.15, 1.0)
    return frac


def _occupancy_series(
    index: pd.DatetimeIndex, kind: str, max_occupancy: int, rng: np.random.Generator
) -> np.ndarray:
    sched = SCHEDULES[kind]
    hour = index.hour.to_numpy()
    dow = index.dayofweek.to_numpy()
    occ = np.zeros(len(index), dtype=float)
    for d in range(7):
        window = sched[d]
        day_mask = dow == d
        if window is None:
            # closed day: rare technician/security visits
            occ[day_mask] = rng.poisson(0.15, size=day_mask.sum())
            continue
        start, end = window
        frac = _occupancy_fraction(hour, start, end)
        weekday_factor = 1.0 if d < 5 else 0.55
        noisy = frac * max_occupancy * weekday_factor
        noisy = noisy * rng.normal(1.0, 0.12, size=len(index))
        occ[day_mask] = np.clip(noisy[day_mask], 0, max_occupancy * 1.1)
        # small spillover just outside hours (early arrivals / late leavers)
        spillover_mask = day_mask & (~((hour >= start) & (hour < end)))
        occ[spillover_mask] += rng.poisson(0.3, size=spillover_mask.sum())
    return np.round(occ).astype(int)


def _hvac_power(
    temp_c: np.ndarray, occupied_mask: np.ndarray, operating_mask: np.ndarray, rated_kw: float, rng
) -> np.ndarray:
    thermal_load = np.clip(np.abs(temp_c - HVAC_SETPOINT_C) / 15.0, 0, 1.6)
    active = operating_mask | occupied_mask
    base = np.where(active, 0.25 * rated_kw, 0.04 * rated_kw)
    variable = np.where(active, thermal_load * rated_kw * 0.85, thermal_load * rated_kw * 0.05)
    power = base + variable
    power *= rng.normal(1.0, 0.05, size=len(temp_c))
    return np.clip(power, 0, rated_kw * 1.4)


def _lighting_power(occupancy: np.ndarray, max_occ: int, operating_mask: np.ndarray, rated_kw: float, rng) -> np.ndarray:
    occ_ratio = np.clip(occupancy / max(max_occ, 1), 0, 1)
    power = np.where(operating_mask, rated_kw * (0.3 + 0.7 * occ_ratio), rated_kw * 0.03)
    power *= rng.normal(1.0, 0.04, size=len(occupancy))
    return np.clip(power, 0, rated_kw * 1.1)


def _equipment_power(zone_type: str, operating_mask: np.ndarray, rated_kw: float, rng) -> np.ndarray:
    n = len(operating_mask)
    if zone_type == "server_room":
        power = rated_kw * rng.normal(0.88, 0.03, size=n)
    else:
        power = np.where(operating_mask, rated_kw * rng.normal(0.85, 0.06, size=n), rated_kw * rng.normal(0.35, 0.05, size=n))
    return np.clip(power, 0, rated_kw * 1.2)


class SyntheticEnergyGenerator:
    def __init__(self, buildings: list[BuildingSpec], start: pd.Timestamp, end: pd.Timestamp, seed: int = 42):
        self.buildings = buildings
        self.index = pd.date_range(start, end, freq="h", inclusive="left")
        self.rng = np.random.default_rng(seed)
        self.ground_truth: list[GroundTruthAnomaly] = []
        self._gt_counter = 0

    def _next_gt_id(self) -> str:
        self._gt_counter += 1
        return f"GT-{self._gt_counter:03d}"

    def generate(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[GroundTruthAnomaly]]:
        weather_rows = []
        reading_rows = []
        occupancy_rows = []

        for building in self.buildings:
            operating_mask = _operating_mask(self.index, building.kind)
            temp_c = _weather_series(self.index, self.rng)
            weather_rows.append(
                pd.DataFrame(
                    {
                        "building_id": building.id,
                        "timestamp": self.index,
                        "temperature_c": temp_c,
                        "humidity_pct": np.clip(self.rng.normal(50, 8, size=len(self.index)), 20, 90),
                    }
                )
            )

            zone_by_id = {z.id: z for f in building.floors for z in f.zones}
            zone_power: dict[str, np.ndarray] = {}
            zone_occ: dict[str, np.ndarray] = {}

            for zone_id, zone in zone_by_id.items():
                occ = _occupancy_series(self.index, building.kind, zone.max_occupancy, self.rng)
                occupied_mask = occ >= max(1, zone.max_occupancy * 0.05)
                zone_occ[zone_id] = occ
                occupancy_rows.append(
                    pd.DataFrame({"zone_id": zone_id, "timestamp": self.index, "occupant_count": occ})
                )

                components: dict[str, np.ndarray] = {}
                for asset in zone.assets:
                    if asset.asset_type == "hvac":
                        arr = _hvac_power(temp_c, occupied_mask, operating_mask, asset.rated_power_kw, self.rng)
                    elif asset.asset_type == "lighting":
                        arr = _lighting_power(occ, zone.max_occupancy, operating_mask, asset.rated_power_kw, self.rng)
                    else:
                        arr = _equipment_power(zone.zone_type, operating_mask, asset.rated_power_kw, self.rng)
                    components[asset.asset_type] = arr

                self._inject_zone_anomalies(building, zone, components, operating_mask, occupied_mask)

                zone_power[zone_id] = sum(components.values())

            # building main meter = sum of zones + common-area/base load
            base_load = building.area_sqm * 0.0025 * (1 + 0.15 * np.sin(2 * np.pi * self.index.hour.to_numpy() / 24))
            total = sum(zone_power.values()) + base_load
            total = self._inject_building_anomalies(building, total)

            main_meter = next(m for m in building.meters if m.meter_type == "main")
            reading_rows.append(
                self._rows_for_meter(main_meter, building.id, total, temp_c, None)
            )

            for meter in building.meters:
                if meter.meter_type == "main":
                    continue
                power = zone_power[meter.zone_id]
                occ = zone_occ[meter.zone_id]
                reading_rows.append(
                    self._rows_for_meter(meter, building.id, power, temp_c, occ, operating_mask=operating_mask)
                )

        readings_df = pd.concat(reading_rows, ignore_index=True)
        weather_df = pd.concat(weather_rows, ignore_index=True)
        occupancy_df = pd.concat(occupancy_rows, ignore_index=True)
        return readings_df, weather_df, occupancy_df, self.ground_truth

    def _rows_for_meter(self, meter, building_id, power_kw, temp_c, occupancy, operating_mask=None):
        n = len(self.index)
        if operating_mask is None:
            operating_state = np.full(n, "n/a", dtype=object)
        else:
            operating_state = np.where(operating_mask, "occupied", "unoccupied")
        return pd.DataFrame(
            {
                "meter_id": meter.id,
                "building_id": building_id,
                "zone_id": meter.zone_id,
                "asset_id": meter.asset_id,
                "timestamp": self.index,
                "power_kw": np.clip(power_kw, 0, None),
                "energy_kwh": np.clip(power_kw, 0, None),  # 1-hour intervals
                "temperature_c": temp_c,
                "occupancy": occupancy if occupancy is not None else np.full(n, None, dtype=object),
                "operating_state": operating_state,
                "data_quality": "valid",
                "source": "synthetic",
            }
        )

    def _inject_zone_anomalies(self, building, zone, components, operating_mask, occupied_mask):
        """Inject after-hours HVAC runs and elevated-baseline events at the asset level."""
        n = len(self.index)
        hvac = components.get("hvac")
        if hvac is None:
            return

        submeter_id = next(
            m.id for m in building.meters if m.zone_id == zone.id
        )

        # After-hours HVAC: pick ~1 event per zone with ~35% probability, 2-4 hours after schedule end.
        if self.rng.random() < 0.35:
            candidate_days = np.where(~operating_mask)[0]
            off_after_on = np.where(operating_mask[:-1] & ~operating_mask[1:])[0]
            if len(off_after_on) > 0:
                pick = self.rng.integers(0, len(off_after_on))
                start_idx = off_after_on[pick] + 1
                duration = int(self.rng.integers(2, 5))
                end_idx = min(start_idx + duration, n)
                boost = self.rng.uniform(2.2, 3.2)
                asset = next(a for a in zone.assets if a.asset_type == "hvac")
                hvac[start_idx:end_idx] = asset.rated_power_kw * self.rng.uniform(0.55, 0.75) * boost
                self.ground_truth.append(
                    GroundTruthAnomaly(
                        id=self._next_gt_id(),
                        meter_id=submeter_id,
                        building_id=building.id,
                        zone_id=zone.id,
                        anomaly_type="after_hours_hvac",
                        start=self.index[start_idx],
                        end=self.index[end_idx - 1],
                        description=f"Injected after-hours HVAC run on {asset.id}",
                    )
                )

        # Unusual sustained elevated base load (~15% chance per zone)
        if self.rng.random() < 0.15:
            start_idx = int(self.rng.integers(0, n - 96))
            duration = int(self.rng.integers(48, 96))  # 2-4 days
            end_idx = min(start_idx + duration, n)
            hvac[start_idx:end_idx] *= self.rng.uniform(1.4, 1.8)
            self.ground_truth.append(
                GroundTruthAnomaly(
                    id=self._next_gt_id(),
                    meter_id=submeter_id,
                    building_id=building.id,
                    zone_id=zone.id,
                    anomaly_type="unusual_base_load",
                    start=self.index[start_idx],
                    end=self.index[end_idx - 1],
                    description="Injected sustained elevated baseline (possible degraded equipment)",
                )
            )

        # Sensor outage: reading gets stuck at a flat value (~12% chance per zone)
        if self.rng.random() < 0.12:
            start_idx = int(self.rng.integers(0, n - 12))
            duration = int(self.rng.integers(5, 11))
            end_idx = min(start_idx + duration, n)
            stuck_value = float(hvac[start_idx])
            hvac[start_idx:end_idx] = stuck_value
            self.ground_truth.append(
                GroundTruthAnomaly(
                    id=self._next_gt_id(),
                    meter_id=submeter_id,
                    building_id=building.id,
                    zone_id=zone.id,
                    anomaly_type="sensor_outage",
                    start=self.index[start_idx],
                    end=self.index[end_idx - 1],
                    description="Injected stale/stuck sensor reading",
                )
            )

        components["hvac"] = hvac

    def _inject_building_anomalies(self, building, total: np.ndarray) -> np.ndarray:
        """Inject a short building-level peak-demand excursion and a one-off meter spike."""
        n = len(total)
        main_meter_id = next(m.id for m in building.meters if m.meter_type == "main")

        if self.rng.random() < 0.6:
            hot_hours = np.where(total > np.percentile(total, 85))[0]
            if len(hot_hours) > 0:
                start_idx = int(self.rng.choice(hot_hours))
                duration = int(self.rng.integers(1, 3))
                end_idx = min(start_idx + duration, n)
                total[start_idx:end_idx] *= self.rng.uniform(1.25, 1.45)
                self.ground_truth.append(
                    GroundTruthAnomaly(
                        id=self._next_gt_id(),
                        meter_id=main_meter_id,
                        building_id=building.id,
                        zone_id=None,
                        anomaly_type="peak_demand_event",
                        start=self.index[start_idx],
                        end=self.index[end_idx - 1],
                        description="Injected peak-demand excursion on the building main meter",
                    )
                )

        if self.rng.random() < 0.5:
            idx = int(self.rng.integers(0, n))
            total[idx] *= self.rng.uniform(2.5, 4.0)
            self.ground_truth.append(
                GroundTruthAnomaly(
                    id=self._next_gt_id(),
                    meter_id=main_meter_id,
                    building_id=building.id,
                    zone_id=None,
                    anomaly_type="meter_spike",
                    start=self.index[idx],
                    end=self.index[idx],
                    description="Injected single-interval meter spike",
                )
            )

        return total
