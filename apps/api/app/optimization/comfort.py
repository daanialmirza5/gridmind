"""Comfort model: the optimizer must never trade energy savings for an impossible or
uncomfortable schedule. Bounds below are explicit, configurable demo assumptions."""

from dataclasses import dataclass

OCCUPIED_COMFORT_RANGE_C = (21.0, 24.0)
UNOCCUPIED_COMFORT_RANGE_C = (18.0, 27.0)


@dataclass
class ComfortAssessment:
    impact: str  # None, Low, Medium, High
    violations: int
    notes: str


def assess_setpoint_change(base_setpoint_c: float, delta_c: float) -> ComfortAssessment:
    new_setpoint = base_setpoint_c + delta_c
    lo, hi = OCCUPIED_COMFORT_RANGE_C
    if new_setpoint < lo or new_setpoint > hi:
        violations = 1
        breach = (lo - new_setpoint) if new_setpoint < lo else (new_setpoint - hi)
        return ComfortAssessment(
            impact="High",
            violations=violations,
            notes=f"New setpoint {new_setpoint:.1f}C breaches the occupied comfort range "
            f"({lo:.0f}-{hi:.0f}C) by {breach:.1f}C.",
        )
    magnitude = abs(delta_c)
    if magnitude <= 1.0:
        return ComfortAssessment("Low", 0, "Setpoint change stays well within the occupied comfort range.")
    if magnitude <= 3.0:
        return ComfortAssessment("Medium", 0, "Setpoint change stays within the occupied comfort range but is noticeable.")
    return ComfortAssessment("High", 0, "Large setpoint change; occupants likely to notice even though bounds hold.")


def assess_after_hours_cutback(had_spillover_occupancy: bool) -> ComfortAssessment:
    if had_spillover_occupancy:
        return ComfortAssessment(
            "Medium", 1, "Historical data shows occasional occupancy just after scheduled hours; cutback may affect them."
        )
    return ComfortAssessment("Low", 0, "No occupied periods affected — this window is reliably unoccupied.")


def assess_lighting_reduction(reduction_pct: float) -> ComfortAssessment:
    if reduction_pct <= 15:
        return ComfortAssessment("Low", 0, "Minor dimming, unlikely to be noticed.")
    if reduction_pct <= 35:
        return ComfortAssessment("Medium", 0, "Noticeable dimming during occupied hours.")
    return ComfortAssessment("High", 0, "Significant dimming; may affect visual comfort/productivity.")


def assess_peak_shift() -> ComfortAssessment:
    return ComfortAssessment("None", 0, "Pure load-shifting; total conditioning delivered is unchanged.")
