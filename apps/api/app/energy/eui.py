"""Energy Use Intensity: EUI = Energy Consumption / Building Area."""

from dataclasses import dataclass


@dataclass
class EUIResult:
    current_eui_kwh_per_sqm: float
    current_eui_kwh_per_sqft: float
    previous_eui_kwh_per_sqm: float | None
    change_pct: float | None


SQM_TO_SQFT = 10.7639


def compute_eui(current_kwh: float, area_sqm: float, previous_kwh: float | None = None) -> EUIResult:
    if area_sqm <= 0:
        raise ValueError("area_sqm must be positive")

    current_eui = current_kwh / area_sqm
    previous_eui = (previous_kwh / area_sqm) if previous_kwh is not None else None
    change_pct = None
    if previous_eui is not None and previous_eui > 0:
        change_pct = round(((current_eui - previous_eui) / previous_eui) * 100, 2)

    return EUIResult(
        current_eui_kwh_per_sqm=round(current_eui, 3),
        current_eui_kwh_per_sqft=round(current_eui / SQM_TO_SQFT, 4),
        previous_eui_kwh_per_sqm=round(previous_eui, 3) if previous_eui is not None else None,
        change_pct=change_pct,
    )
