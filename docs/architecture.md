# GridMind Architecture

```text
                   GRIDMIND
                       |
              +--------+--------+
              |                 |
        ENERGY INGESTION    SYNTHETIC DATA
              |                 |
              +--------+--------+
                       |
                DATA QUALITY
                       |
                ENERGY LEDGER
                       |
          +------------+------------+
          |            |            |
       BASELINE     FORECAST     ANOMALIES
          |            |            |
          +------------+------------+
                       |
                 WASTE ENGINE
                       |
               DIGITAL TWIN
                       |
              OPTIMIZATION LAB
                       |
             SCENARIO SIMULATION
                       |
              RECOMMENDATION
                       |
                AI ANALYST
                       |
               HUMAN APPROVAL
                       |
                 AUDIT TRAIL
```

## Repository layout

The build brief suggested a `packages/` workspace split (domain, energy, forecasting,
optimization, ai, shared as separate publishable packages). For a project of this size,
that split adds real overhead (cross-package versioning, build ordering) without a
second consumer to justify it, so GridMind instead organizes the same boundaries as
Python modules inside one FastAPI service:

```text
gridmind/
├── apps/
│   ├── web/                     Next.js 14 (App Router) + TypeScript + Tailwind
│   │   ├── app/                 one folder per route (dashboard, buildings, energy, ...)
│   │   ├── components/           ui.tsx, Shell.tsx, charts.tsx, twin/ (React Flow graphs)
│   │   └── lib/                  api.ts, auth.tsx, hooks.ts (TanStack Query), types.ts
│   │
│   └── api/                     FastAPI + SQLAlchemy + pandas/numpy/statsmodels
│       ├── app/
│       │   ├── core/              config, database, security (JWT + RBAC), errors, rate limiting
│       │   ├── domain/            SQLAlchemy models (the entity list in the brief)
│       │   ├── energy/            ingestion, data quality, ledger queries, cost, carbon, EUI, baseline, waste rules
│       │   ├── ml/                 anomaly detection, forecasting + evaluation
│       │   ├── optimization/       comfort model, scenario simulator, recommendation engine
│       │   ├── ai/                 provider abstraction, agents, evidence retrieval, guardrails
│       │   └── api/routers/        one FastAPI router per resource
│       ├── seed/                  synthetic building/meter generator + full seed pipeline
│       ├── scripts/                evaluate_models.py -- writes docs/evaluation_report.md
│       └── tests/                  unit/ + integration/
│
├── tests/e2e/                    Playwright, targets the running web+api pair
├── docs/                          this file, model_cards.md, evaluation_report.md
├── .github/workflows/ci.yml
└── docker-compose.yml
```

## Why FastAPI + one Python service instead of a polyglot stack

The brief's "preferred" stack was FastAPI for the backend, which GridMind follows.
Everything that matters for the "real engineering, not a chatbot" bar -- the ingestion
pipeline, the statistical baseline/anomaly model, the rule-based waste engine, the
Holt-Winters forecaster, the scenario simulator, the recommendation prioritizer -- lives
in plain, testable Python modules with no framework coupling, so they're unit-tested
directly (see `apps/api/tests/unit`) rather than only reachable through HTTP.

## Data flow for one "why did energy spike" investigation

1. `seed/run_seed.py` generates 6 months of hourly synthetic readings for 3 buildings
   (`seed/timeseries.py`), deliberately injecting known anomalies and imperfect data,
   and writes everything into the `meter_readings` ledger table.
2. `app/energy/baseline.py` buckets historical readings by (meter, day-of-week,
   hour-of-day) to produce an "expected" value and standard deviation per bucket.
3. `app/ml/anomaly.py` compares each reading to its bucket's expected value using a
   combined rolling z-score + IQR check, and only flags a reading when *both* agree it's
   unusual -- see the anomaly detection docstring for why.
4. `app/energy/waste.py` runs four deterministic IF/THEN rules over the same baseline
   comparison (after-hours HVAC, low-occupancy high-draw, sustained elevated baseline,
   repeated peak-demand events), each carrying the exact numbers that triggered it.
5. `app/optimization/recommendations.py` groups waste events into one recommendation per
   (building, zone, rule), estimates savings from the actual waste totals, and ranks them
   with a transparent weighted score (savings x0.5 + confidence x0.3 + (1-effort) x0.2).
6. A human (via `/api/recommendations/{id}/approve`) approves or rejects it; either way,
   an `AuditEvent` row is written with the actor, previous/new state, and reason.
7. If the user asks the AI Analyst "why did energy spike," `app/ai/service.py` routes the
   question to the `anomaly_analyst` agent, pulls the last N anomalies as structured
   evidence, and asks the configured provider (or the Mock provider, offline) to narrate
   -- never to compute -- that evidence.

## Known simplifications (see docs/model_cards.md for detail)

- Each zone has one aggregated submeter (HVAC + lighting + equipment combined), not one
  meter per asset, so "why was HVAC-014 flagged" evidence is inferred from the submeter's
  behavior during hours where the other loads are near-zero, not read from an isolated
  HVAC-only signal.
- The optimization simulator adjusts historical readings with documented, named
  constants (e.g. `HVAC_THERMAL_SENSITIVITY = 0.35`) rather than a full building-physics
  model -- reasonable for a what-if demo, explicitly not a certified energy model.
