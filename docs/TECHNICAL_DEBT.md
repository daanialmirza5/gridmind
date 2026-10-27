# GridMind — Technical Debt & Architectural Audit

**Repository**: `gridmind`  

## Prioritized Debt Items
- **[P1 — High] WebSocket Telemetry Streaming**: Current UI polls API every 3s. Should implement native WebSocket pub/sub for sub-second telemetry updates.
- **[P2 — Medium] Mixed-Integer Linear Programming (MILP) Solver Integration**: Replace greedy heuristics with HiGHS / SciPy linprog for globally optimal multi-day dispatch.
- **[P3 — Low] Historical Data Partitioning**: Timeseries table needs date-based partitioning in PostgreSQL for multi-year historical retention.
