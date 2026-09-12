"""Energy forecasting engine.

Two methods, in increasing order of sophistication:
  - seasonal_naive: forecast(t) = actual value from the same hour-of-week one cycle back
    (168h). Simple, robust, hard to beat for strongly seasonal building loads, and used
    as the honest baseline forecast evaluation compares against.
  - holt_winters: statsmodels Holt-Winters exponential smoothing with a 24-hour seasonal
    period, fit on the building's aggregated main-meter series.

Uncertainty intervals are derived from the in-sample residual standard deviation of the
fitted model (a 90% interval, expected +/- 1.645*sigma) — approximate, and explicitly
labeled as a forecast interval rather than a guarantee.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

SEASONAL_PERIOD = 24
CONFIDENCE_Z = 1.645  # ~90% interval


@dataclass
class ForecastPoint:
    timestamp: pd.Timestamp
    expected_kwh: float
    lower_kwh: float
    upper_kwh: float


@dataclass
class ForecastResult:
    method: str
    points: list[ForecastPoint]
    residual_std: float


def seasonal_naive_forecast(history: pd.Series, horizon_hours: int) -> ForecastResult:
    if len(history) < SEASONAL_PERIOD * 7:
        raise ValueError("Not enough history for seasonal_naive forecast (need >= 7 days)")

    last_week = history.iloc[-24 * 7 :]
    residual_std = float(history.diff(24 * 7).dropna().std()) if len(history) > 24 * 7 else float(history.std())

    points = []
    last_ts = history.index[-1]
    for h in range(1, horizon_hours + 1):
        ts = last_ts + pd.Timedelta(hours=h)
        source_idx = (h - 1) % (24 * 7)
        expected = float(last_week.iloc[source_idx])
        points.append(
            ForecastPoint(
                timestamp=ts,
                expected_kwh=round(expected, 2),
                lower_kwh=round(max(expected - CONFIDENCE_Z * residual_std, 0), 2),
                upper_kwh=round(expected + CONFIDENCE_Z * residual_std, 2),
            )
        )
    return ForecastResult(method="seasonal_naive", points=points, residual_std=round(residual_std, 3))


def holt_winters_forecast(history: pd.Series, horizon_hours: int) -> ForecastResult:
    if len(history) < SEASONAL_PERIOD * 14:
        raise ValueError("Not enough history for holt_winters forecast (need >= 14 days)")

    clipped = history.clip(lower=0.01)
    if clipped.index.freq is None:
        clipped = clipped.asfreq("h")
        clipped = clipped.interpolate(limit_direction="both")
    model = ExponentialSmoothing(
        clipped, trend="add", seasonal="add", seasonal_periods=SEASONAL_PERIOD, damped_trend=True
    ).fit(optimized=True)

    residual_std = float(model.resid.std())
    forecast_values = model.forecast(horizon_hours)

    points = []
    for ts, expected in zip(forecast_values.index, forecast_values.values):
        expected = max(float(expected), 0.0)
        points.append(
            ForecastPoint(
                timestamp=pd.Timestamp(ts),
                expected_kwh=round(expected, 2),
                lower_kwh=round(max(expected - CONFIDENCE_Z * residual_std, 0), 2),
                upper_kwh=round(expected + CONFIDENCE_Z * residual_std, 2),
            )
        )
    return ForecastResult(method="holt_winters", points=points, residual_std=round(residual_std, 3))


def generate_forecast(history: pd.Series, horizon_hours: int, method: str = "holt_winters") -> ForecastResult:
    if method == "seasonal_naive":
        return seasonal_naive_forecast(history, horizon_hours)
    try:
        return holt_winters_forecast(history, horizon_hours)
    except Exception:
        # Fall back to the simpler, more robust baseline rather than failing the request.
        return seasonal_naive_forecast(history, horizon_hours)


@dataclass
class EvaluationResult:
    horizon_label: str
    horizon_hours: int
    method: str
    mae: float
    rmse: float
    mape: float
    n_points: int


def evaluate_forecast(history: pd.Series, horizon_hours: int, method: str = "holt_winters") -> EvaluationResult | None:
    """Holdout backtest: fit on everything before the last `horizon_hours`, forecast that
    window, and score against the actual values that really occurred."""
    if len(history) <= horizon_hours + SEASONAL_PERIOD * 14:
        return None

    train = history.iloc[:-horizon_hours]
    actual = history.iloc[-horizon_hours:]

    result = generate_forecast(train, horizon_hours, method=method)
    predicted = np.array([p.expected_kwh for p in result.points])
    actual_values = actual.values

    errors = predicted - actual_values
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    nonzero = actual_values != 0
    mape = float(np.mean(np.abs(errors[nonzero] / actual_values[nonzero])) * 100) if nonzero.any() else float("nan")

    return EvaluationResult(
        horizon_label=f"{horizon_hours}h",
        horizon_hours=horizon_hours,
        method=result.method,
        mae=round(mae, 3),
        rmse=round(rmse, 3),
        mape=round(mape, 2),
        n_points=len(actual),
    )


@dataclass
class PeakPrediction:
    expected_peak_timestamp: pd.Timestamp
    expected_peak_kw: float
    historical_peak_kw: float
    risk: str


def predict_peak_demand(forecast: ForecastResult, historical_peak_kw: float) -> PeakPrediction:
    """Uses the forecast's upper confidence bound (not just the point estimate) to flag
    peak-demand risk conservatively — the whole point of predicting a peak is not being
    surprised by it."""
    best = max(forecast.points, key=lambda p: p.upper_kwh)
    ratio = best.upper_kwh / historical_peak_kw if historical_peak_kw > 0 else 0
    if ratio >= 0.95:
        risk = "HIGH"
    elif ratio >= 0.80:
        risk = "MEDIUM"
    else:
        risk = "LOW"
    return PeakPrediction(
        expected_peak_timestamp=best.timestamp,
        expected_peak_kw=best.expected_kwh,
        historical_peak_kw=round(historical_peak_kw, 1),
        risk=risk,
    )
