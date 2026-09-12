import pytest

from app.energy.eui import compute_eui


def test_eui_basic_conversion():
    result = compute_eui(current_kwh=1000, area_sqm=500)
    assert result.current_eui_kwh_per_sqm == pytest.approx(2.0)
    assert result.current_eui_kwh_per_sqft == pytest.approx(2.0 / 10.7639, rel=1e-3)


def test_eui_change_pct_against_previous_period():
    result = compute_eui(current_kwh=1200, area_sqm=500, previous_kwh=1000)
    assert result.previous_eui_kwh_per_sqm == pytest.approx(2.0)
    assert result.current_eui_kwh_per_sqm == pytest.approx(2.4)
    assert result.change_pct == pytest.approx(20.0)


def test_eui_rejects_non_positive_area():
    with pytest.raises(ValueError):
        compute_eui(current_kwh=100, area_sqm=0)
