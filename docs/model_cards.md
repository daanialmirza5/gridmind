# GridMind Model Cards

Every model below runs against **synthetic data only**. Numbers in this document (and in
`docs/evaluation_report.md`) come from actually running these models against the seeded
dataset -- none are estimated or invented.

---

## Baseline Model (`app/energy/baseline.py`)

**Purpose:** estimate expected energy consumption "under normal conditions" for a given
meter and hour, as the reference point anomaly and waste detection compare against.

**Method:** bucket every historical hourly reading for a meter by `(day_of_week,
hour_of_day)` (168 buckets/week) and take the mean and standard deviation of `energy_kwh`
within each bucket.

**Inputs:** the meter's own historical readings only.

**Assumptions / limitations:**
- Does not condition directly on outdoor temperature or a forecasted occupancy value --
  those signals are folded in implicitly (a bucket's mean averages over many days at
  varying temperatures), not modeled explicitly.
- A meter needs enough history for a bucket to be statistically meaningful; buckets with
  very few samples (e.g. early in the 6-month window) have a noisier standard deviation.
- Recomputed periodically (`compute_and_store_baselines`), not updated online per-reading.

**Evaluation:** no separate holdout for the baseline itself -- it's evaluated indirectly
through anomaly detection performance below, since anomaly detection is entirely
downstream of it.

---

## Anomaly Detection (`app/ml/anomaly.py`)

**Purpose:** flag energy readings that are statistically unusual for their meter and
time-of-week.

**Method:** combines two checks, both of which must agree before a reading is flagged:
1. **Robust baseline z-score**: `(actual - expected) / std_dev` using the baseline
   bucket above (falls back to `expected * 0.1` when a bucket's own std is near zero).
2. **IQR check**: is the reading outside `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]` of that meter's
   overall distribution.

A reading is flagged only if `|z| >= 2.2`, the IQR check also agrees, and the deviation
is at least 15% -- three independent guards against flagging normal noise.

**Evaluation** (see `docs/evaluation_report.md` for the actual run):
Measured against the generator's own injected ground-truth anomalies
(`seed/output/ground_truth_anomalies.json`), with a +/-2h matching tolerance. Precision
and recall are reported honestly, including when they are unflattering -- e.g. many
detections are real statistical outliers that were never deliberately injected, so they
count as neither a true nor a false positive against the ground truth (there is no label
for them either way); this is disclosed in the report rather than hidden.

**Limitations:** thresholds are fixed constants, not tuned via a validation set; a
production system would tune them per-meter-class using a labeled dataset.

---

## Waste Detection (`app/energy/waste.py`)

**Purpose:** deterministic, auditable rules that flag specific waste *patterns*, not just
statistical outliers.

**Rules implemented:**
| Rule | Condition |
|---|---|
| `after_hours_hvac` | occupancy < 3 AND energy > 1.5x expected AND outside operating schedule |
| `high_energy_low_occupancy` | occupancy < 10% of zone max AND energy > 60% of typical occupied load, during operating hours (server rooms excluded -- always-on load there is legitimate) |
| `excessive_standby_load` | deviation > 30% above baseline sustained for >= 24 consecutive hours |
| `repeated_peak_demand_events` | building main meter hits its own 90th-percentile power on 3+ separate occasions within a rolling 7-day window |

**Not implemented** (present in the original design brief, explicitly dropped rather than
faked): "simultaneous heating/cooling" and "equipment running outside schedule" as
*separate* signals. GridMind's zone submeters aggregate HVAC + lighting + equipment into
one reading (see the digital twin's meter model), so there is no independent per-asset
telemetry to test either condition against. A future iteration with per-asset submetering
could add both.

**Estimated impact:** every `WasteEvent` stores the observed vs. expected kWh for its
window; cost and CO2e are derived by running that delta kWh back through the same
cost/carbon engines used everywhere else (`app/energy/cost.py`, `app/energy/carbon.py`).

---

## Forecasting (`app/ml/forecast.py`)

**Method:** two options.
- `seasonal_naive`: forecast(t) = the actual value from 168 hours (1 week) earlier.
  Simple, robust, and the honest baseline other methods are compared to.
- `holt_winters`: statsmodels' Holt-Winters exponential smoothing, additive trend +
  24-hour additive seasonality, damped trend.

`generate_forecast()` tries Holt-Winters and falls back to `seasonal_naive` if the model
fails to fit (e.g. not enough history) -- the app never returns an error where a simpler
answer would do.

**Uncertainty:** a symmetric interval of `expected +/- 1.645 * residual_std` (~90%),
where `residual_std` is the in-sample residual standard deviation of whichever model was
actually fit. This is an approximation, not a proper prediction interval from the model's
own likelihood -- explicitly labeled as such in the UI ("forecast interval," not "range
we guarantee").

**Evaluation:** walk-forward holdout backtest -- fit on everything before the holdout
window, forecast blind, score against what actually happened. Run for 24h/7d/30d
horizons per building; see `docs/evaluation_report.md` for the real MAE/RMSE/MAPE
numbers. MAPE increases with horizon length, which is expected (compounding weather and
occupancy uncertainty), not something to be alarmed by or to hide.

---

## Optimization / Scenario Simulator (`app/optimization/simulator.py`, `engine.py`)

**Purpose:** estimate the effect of policy levers (setpoint change, after-hours cutback,
lighting dimming, peak-load shifting) on historical energy, cost, peak demand, and
emissions, without needing a full building-physics model.

**Method (per lever, all constants named and adjustable in `simulator.py`):**
- **Setpoint**: additive adjustment using the same thermal-load formula the synthetic
  generator uses (`|temp - setpoint| / 15`, clipped 0-1.6), scaled by the zone's real
  rated HVAC power and a documented `HVAC_THERMAL_SENSITIVITY = 0.35` share of
  operating-hour load. Deliberately additive rather than a ratio of the current reading,
  because a ratio-based version historically blew up when the baseline thermal load was
  near zero (regression-tested in `tests/unit/test_optimization.py`).
- **After-hours cutback**: for N hours after the schedule closes, pulls the reading
  toward the meter's own after-hours 10th-percentile ("deep standby") value, closing 80%
  of the gap (`AFTER_HOURS_CUTBACK_EFFECTIVENESS`).
- **Lighting reduction**: a flat % applied to the estimated lighting share of
  operating-hour load (`LIGHTING_SHARE_OF_NON_HVAC = 0.50`), skipped for server rooms
  (no lighting asset).
- **Peak shift**: moves up to `shift_kw` out of the tariff's peak window into that same
  day's off-peak hours, energy-neutral by construction (verified in tests).

Setpoint/cutback/lighting changes are computed on zone submeters only, then the total
zone-level delta for each timestamp is added to the building main meter -- rather than
re-applying an asset-level formula to an aggregate reading that isn't a single asset.

**Comfort model:** occupied comfort range 21-24C, unoccupied 18-27C (both configurable,
demo assumptions). A setpoint change outside the occupied range is a hard violation, not
just a warning.

**Objective scoring:** `objective = w_cost*cost% + w_energy*energy% + w_emissions*emissions% + w_peak*peak%`
(lower is better). The "balanced" weights (0.45/0.30/0.15/0.10) match the design brief
exactly; cost/energy/emissions/peak presets weight their own metric at 0.70.

**Limitations:** this is a transparent approximation for a what-if demo, not a certified
energy model -- see the "known simplifications" note in `docs/architecture.md`.

---

## Carbon Engine (`app/energy/carbon.py`)

`CO2e = energy_consumption_kWh x emission_factor`. The factor
(`EmissionFactor.factor_kg_co2e_per_kwh`, default 0.417) is stored with
`is_synthetic_assumption=True` and a source/region label, and every API response and UI
panel that shows a carbon number repeats that it is a demo assumption, not an official
grid figure.

## Cost Engine (`app/energy/cost.py`)

`cost = consumption_cost (split peak/off-peak under the tariff) + demand_cost (billing-period peak kW x demand charge)`.
Tariffs are stored with `is_synthetic_assumption=True` for the same reason.

## Savings Estimation (`app/optimization/recommendations.py`)

Every recommendation's `estimated_*_savings` fields are a straight rollup of the actual
`WasteEvent` rows in its group (see the Waste Detection section) -- never a separately
invented number. The API and UI both attach the disclaimer: *"Estimated potential impact
based on synthetic data and model assumptions -- not a guaranteed savings figure."*

## Asset Health (`app/api/routers/structure.py::get_asset_health`)

Explicitly a **heuristic**, not a trained predictive-maintenance model: efficiency is
scored as `100 - |utilization - 0.6| * 80`, where utilization is the last 7 days' average
power over rated power. The API response carries `health_is_heuristic: true` and a
`health_note` string, and the UI surfaces that note next to the health badge rather than
presenting it as a certified diagnosis.
