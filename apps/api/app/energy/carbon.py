"""Deterministic carbon (CO2e) engine: CO2e = energy_consumption x emission_factor.

Emission factors are configurable and explicitly labeled as demo assumptions —
never presented as official government or utility figures.
"""

from dataclasses import dataclass

import pandas as pd

from app.domain.energy import EmissionFactor


@dataclass
class EmissionsResult:
    total_kg_co2e: float
    factor_used: float
    factor_source: str
    factor_region: str
    is_synthetic_assumption: bool


def compute_emissions(readings: pd.DataFrame, factor: EmissionFactor) -> EmissionsResult:
    total_kwh = float(readings["energy_kwh"].sum()) if not readings.empty else 0.0
    total_kg = total_kwh * factor.factor_kg_co2e_per_kwh
    return EmissionsResult(
        total_kg_co2e=round(total_kg, 2),
        factor_used=factor.factor_kg_co2e_per_kwh,
        factor_source=factor.source,
        factor_region=factor.region,
        is_synthetic_assumption=factor.is_synthetic_assumption,
    )
