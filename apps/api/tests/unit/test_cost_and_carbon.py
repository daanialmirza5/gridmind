import pandas as pd
import pytest

from app.domain.energy import EmissionFactor, Tariff
from app.energy.carbon import compute_emissions
from app.energy.cost import compute_cost


def _tariff(**overrides) -> Tariff:
    defaults = dict(
        id="t1", building_id="b1", name="Test", tariff_type="flat", currency="USD",
        flat_rate_per_kwh=0.20, peak_rate_per_kwh=0.30, off_peak_rate_per_kwh=0.10,
        peak_start_hour=14, peak_end_hour=19, demand_charge_per_kw=10.0, is_synthetic_assumption=True,
    )
    defaults.update(overrides)
    return Tariff(**defaults)


def test_flat_tariff_cost_is_rate_times_energy():
    readings = pd.DataFrame(
        {"timestamp": pd.date_range("2026-01-01", periods=3, freq="h"), "energy_kwh": [10, 10, 10], "power_kw": [10, 10, 10]}
    )
    result = compute_cost(readings, _tariff(tariff_type="flat"))
    assert result.consumption_cost == pytest.approx(30 * 0.20)
    assert result.demand_cost == pytest.approx(10 * 10.0)
    assert result.total_cost == pytest.approx(result.consumption_cost + result.demand_cost)


def test_time_of_use_splits_peak_and_off_peak():
    timestamps = [pd.Timestamp("2026-01-01 14:00"), pd.Timestamp("2026-01-01 08:00")]
    readings = pd.DataFrame({"timestamp": timestamps, "energy_kwh": [5, 5], "power_kw": [5, 5]})
    result = compute_cost(readings, _tariff(tariff_type="time_of_use"))
    assert result.peak_cost == pytest.approx(5 * 0.30)
    assert result.off_peak_cost == pytest.approx(5 * 0.10)


def test_empty_readings_produce_zero_cost():
    result = compute_cost(pd.DataFrame(columns=["timestamp", "energy_kwh", "power_kw"]), _tariff())
    assert result.total_cost == 0


def test_emissions_scale_linearly_with_energy():
    factor = EmissionFactor(
        id="ef1", source="grid", region="X", factor_kg_co2e_per_kwh=0.5, is_synthetic_assumption=True
    )
    readings = pd.DataFrame({"energy_kwh": [100, 200]})
    result = compute_emissions(readings, factor)
    assert result.total_kg_co2e == pytest.approx(150.0)
    assert result.is_synthetic_assumption is True
