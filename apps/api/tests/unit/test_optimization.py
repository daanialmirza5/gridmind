import pandas as pd
import pytest

from app.domain.energy import Tariff
from app.optimization.comfort import assess_setpoint_change
from app.optimization.simulator import apply_peak_shift, apply_setpoint_lever


def test_setpoint_change_within_bounds_is_not_a_violation():
    result = assess_setpoint_change(22.0, 2.0)
    assert result.violations == 0
    assert result.impact in ("Low", "Medium")


def test_setpoint_change_outside_comfort_bounds_is_a_violation():
    result = assess_setpoint_change(22.0, 5.0)  # 27C, outside occupied range 21-24
    assert result.violations == 1
    assert result.impact == "High"


def test_setpoint_lever_never_blows_up_when_baseline_thermal_load_is_near_zero():
    """Regression test: an earlier ratio-based implementation could multiply energy by
    10x+ when the outdoor temperature was very close to the current setpoint. The
    additive, rated-power-based model must stay bounded regardless of temperature."""
    df = pd.DataFrame(
        {
            "temperature_c": [22.001, 35.0, 5.0],  # first is almost exactly at setpoint
            "energy_kwh": [10.0, 10.0, 10.0],
        }
    )
    rated_kw = pd.Series([20.0, 20.0, 20.0])
    operating_mask = pd.Series([True, True, True])
    adjusted = apply_setpoint_lever(df, delta_c=3.0, operating_mask=operating_mask, rated_kw=rated_kw)
    assert adjusted.max() < 40  # nowhere close to the old bug's 100+ kWh blowup
    assert (adjusted >= 0).all()


def test_setpoint_lever_no_op_when_delta_is_zero():
    df = pd.DataFrame({"temperature_c": [30.0], "energy_kwh": [10.0]})
    result = apply_setpoint_lever(df, 0.0, pd.Series([True]), pd.Series([20.0]))
    assert result.iloc[0] == 10.0


def test_peak_shift_is_energy_neutral_per_meter_per_day():
    ts = pd.date_range("2026-01-01", periods=24, freq="h")
    df = pd.DataFrame({"meter_id": ["M1"] * 24, "timestamp": ts, "energy_kwh": [5.0] * 24})
    tariff = Tariff(
        id="t1", building_id="b1", name="t", tariff_type="time_of_use",
        peak_start_hour=14, peak_end_hour=19, flat_rate_per_kwh=0.1,
        peak_rate_per_kwh=0.3, off_peak_rate_per_kwh=0.1, demand_charge_per_kw=10,
    )
    shifted = apply_peak_shift(df, shift_kw=2.0, tariff=tariff)
    assert shifted.sum() == pytest.approx(df["energy_kwh"].sum(), abs=1e-6)


def test_peak_shift_does_not_mix_energy_across_different_meters():
    """Regression test for a bug where peak-shift grouped rows by date only, moving
    energy between different meters' readings on the same day."""
    ts = pd.date_range("2026-01-01", periods=5, freq="h")
    df = pd.DataFrame(
        {
            "meter_id": ["M1"] * 5 + ["M2"] * 5,
            "timestamp": list(ts) * 2,
            "energy_kwh": [1.0] * 5 + [1000.0] * 5,
        }
    )
    tariff = Tariff(
        id="t1", building_id="b1", name="t", tariff_type="time_of_use",
        peak_start_hour=0, peak_end_hour=3, flat_rate_per_kwh=0.1,
        peak_rate_per_kwh=0.3, off_peak_rate_per_kwh=0.1, demand_charge_per_kw=10,
    )
    shifted = apply_peak_shift(df, shift_kw=2.0, tariff=tariff)
    m1_total = shifted[df["meter_id"] == "M1"].sum()
    m2_total = shifted[df["meter_id"] == "M2"].sum()
    assert m1_total == pytest.approx(5.0, abs=1e-6)
    assert m2_total == pytest.approx(5000.0, abs=1e-6)
