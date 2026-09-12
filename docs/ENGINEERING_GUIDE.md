# GridMind — Engineering Guide & Mastery Document

## 1. What Is GridMind?
GridMind is a **physics-informed energy intelligence and microgrid digital twin platform** designed for industrial facilities, microgrids, and regional distribution networks. It integrates real-time telemetry, solar/wind renewable generation forecasts, dynamic tariff structures, battery energy storage systems (BESS), and controllable loads to optimize energy dispatch, minimize peak demand charges, and detect telemetry anomalies.

## 2. Real-World Problem Solved
1. **Renewable Intermittency**: Solar and wind generation fluctuate unpredictably, causing grid instability and unexpected peak grid draw.
2. **Demand Charge Penalties**: Commercial/industrial operators face punitive demand tariffs when peak power exceeds contract thresholds.
3. **Suboptimal Battery Cycling**: Arbitrary battery charging/discharging degrades battery health without maximizing economic arbitrage.
4. **Telemetry Sensor Faults**: Corrupted or drifted sensor readings lead to dangerous automated control decisions.

## 3. High-Level Architecture
- **Frontend**: Next.js 14, Tailwind CSS, Recharts for dynamic telemetry timeseries, interactive single-line diagrams.
- **Backend API**: FastAPI (Python 3.12), Pydantic v2, PyJWT, SQLAlchemy 2.0.
- **Digital Twin Engine**:
  - `grid_twin.py`: Mathematical simulation of power flow, substation power draw, battery state of charge (SoC), and renewable curtailment.
  - `optimization.py`: Linear programming / greedy dispatch algorithm for battery charge/discharge scheduling under time-of-use (ToU) tariffs.
  - `anomaly_detector.py`: Statistical z-score and moving-window anomaly detection for grid voltage, frequency, and current sensors.
  - `forecasting.py`: Autoregressive and weather-adjusted renewable generation predictor.
- **AI Analyst**: Grounded LLM energy consultant operating over deterministic grid dispatch logs.
- **Data Layer**: SQLite/PostgreSQL storing substation nodes, battery assets, tariffs, and historical telemetry frames.

## 4. Algorithmic Complexity & Optimization Models
- **Battery Dispatch Optimization**: Minimizes grid cost subject to inverter slew rates, capacity limits, and peak demand constraints.
- **Anomaly Detection**: Rolling window z-score with O(1) update step using Welford algorithm for running variance.

## 5. Security & Safety Boundaries
- Hard power limits enforced in code before control signals are emitted.
- All AI recommendations pass through physical plausibility guardrails (voltage +/- 5%, frequency 50 +/- 0.2 Hz).
- Full JWT authentication and role-based access for operator controls.

## 6. Testing Strategy
- Automated pytest suite validating battery SoC preservation, energy conservation invariants, tariff arbitrage, and anomaly alert triggers.
