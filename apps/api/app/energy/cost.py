"""Deterministic energy cost engine.

cost = consumption_cost (rate x kWh, split by peak/off-peak under time-of-use)
     + demand_cost (peak kW in the period x demand charge)

All tariff figures are configurable, explicitly-labeled demo assumptions
(see Tariff.is_synthetic_assumption) — never presented as real utility rates.
"""

from dataclasses import dataclass

import pandas as pd

from app.domain.energy import Tariff


@dataclass
class CostBreakdown:
    consumption_cost: float
    peak_cost: float
    off_peak_cost: float
    demand_cost: float
    total_cost: float
    currency: str
    is_synthetic_assumption: bool


def compute_cost(readings: pd.DataFrame, tariff: Tariff) -> CostBreakdown:
    if readings.empty:
        return CostBreakdown(0, 0, 0, 0, 0, tariff.currency, tariff.is_synthetic_assumption)

    df = readings.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    if tariff.tariff_type == "time_of_use":
        is_peak = (df["timestamp"].dt.hour >= tariff.peak_start_hour) & (
            df["timestamp"].dt.hour < tariff.peak_end_hour
        )
        peak_cost = float((df.loc[is_peak, "energy_kwh"] * tariff.peak_rate_per_kwh).sum())
        off_peak_cost = float((df.loc[~is_peak, "energy_kwh"] * tariff.off_peak_rate_per_kwh).sum())
    else:
        peak_cost = 0.0
        off_peak_cost = float((df["energy_kwh"] * tariff.flat_rate_per_kwh).sum())

    consumption_cost = peak_cost + off_peak_cost
    demand_cost = float(df["power_kw"].max()) * tariff.demand_charge_per_kw if not df.empty else 0.0
    total = consumption_cost + demand_cost

    return CostBreakdown(
        consumption_cost=round(consumption_cost, 2),
        peak_cost=round(peak_cost, 2),
        off_peak_cost=round(off_peak_cost, 2),
        demand_cost=round(demand_cost, 2),
        total_cost=round(total, 2),
        currency=tariff.currency,
        is_synthetic_assumption=tariff.is_synthetic_assumption,
    )
