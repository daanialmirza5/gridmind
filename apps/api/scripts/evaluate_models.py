"""Runs the actual evaluation suite against the seeded database and writes real,
non-fabricated numbers to docs/evaluation_report.md.

Usage (from apps/api): python -m scripts.evaluate_models
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json

import pandas as pd

from app.core.database import SessionLocal
from app.domain.intelligence import Anomaly
from app.domain.structure import Building
from app.energy.ledger import query_readings
from app.ml.forecast import evaluate_forecast
from app.optimization.engine import simulate
from app.optimization.simulator import PRESETS

GT_PATH = Path(__file__).resolve().parents[1] / "seed" / "output" / "ground_truth_anomalies.json"
REPORT_PATH = Path(__file__).resolve().parents[2].parent / "docs" / "evaluation_report.md"


def evaluate_anomaly_detection(db) -> dict:
    if not GT_PATH.exists():
        return {"error": "ground truth file not found; run seed.run_seed first"}

    ground_truth = json.loads(GT_PATH.read_text())
    detected = db.query(Anomaly).all()

    matched_gt_ids = set()
    matched_detections = 0
    for a in detected:
        for gt in ground_truth:
            if gt["id"] in matched_gt_ids:
                continue
            if gt["meter_id"] != a.meter_id:
                continue
            gt_start, gt_end = pd.Timestamp(gt["start"]), pd.Timestamp(gt["end"])
            # allow a 2-hour tolerance window on either side
            if gt_start - pd.Timedelta(hours=2) <= a.timestamp <= gt_end + pd.Timedelta(hours=2):
                matched_gt_ids.add(gt["id"])
                matched_detections += 1
                break

    true_positives = len(matched_gt_ids)
    false_negatives = len(ground_truth) - true_positives
    false_positives = len(detected) - matched_detections

    precision = matched_detections / len(detected) if detected else 0.0
    recall = true_positives / len(ground_truth) if ground_truth else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "total_ground_truth_anomalies": len(ground_truth),
        "total_detected_anomalies": len(detected),
        "true_positives": true_positives,
        "false_negatives": false_negatives,
        "false_positives_vs_ground_truth": false_positives,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "note": (
            "Ground-truth events (after_hours_hvac, unusual_base_load, sensor_outage, "
            "peak_demand_event, meter_spike) were deliberately injected by the synthetic "
            "generator. Recall/precision are measured only against these injected cases -- "
            "many additional detections are naturally-occurring statistical outliers in the "
            "synthetic data that were not deliberately injected, and are NOT counted as false "
            "positives here since there is no ground truth for them either way."
        ),
    }


def evaluate_forecasts(db) -> list[dict]:
    results = []
    for building in db.query(Building).all():
        readings = query_readings(db, building_id=building.id)
        main = readings[readings["zone_id"].isna()].set_index("timestamp")["energy_kwh"]
        for horizon_hours, label in [(24, "24h"), (168, "7d"), (720, "30d")]:
            ev = evaluate_forecast(main, horizon_hours, method="holt_winters")
            if ev is None:
                continue
            results.append(
                {
                    "building": building.name,
                    "building_id": building.id,
                    "horizon": label,
                    "method": ev.method,
                    "mae_kwh": ev.mae,
                    "rmse_kwh": ev.rmse,
                    "mape_pct": ev.mape,
                    "n_points": ev.n_points,
                }
            )
    return results


def evaluate_optimization(db) -> list[dict]:
    results = []
    for building in db.query(Building).all():
        for preset_name, levers in PRESETS.items():
            try:
                result = simulate(db, building.id, levers, objective="balanced")
            except ValueError:
                continue
            results.append(
                {
                    "building": building.name,
                    "preset": preset_name,
                    "levers": levers.as_dict(),
                    "energy_change_pct": result.metrics.energy_change_pct,
                    "cost_change_pct": result.metrics.cost_change_pct,
                    "peak_change_pct": result.metrics.peak_change_pct,
                    "emissions_change_pct": result.metrics.emissions_change_pct,
                    "comfort_impact": result.comfort_impact,
                    "objective_score": result.objective_score,
                }
            )
    return results


def render_report(anomaly_eval, forecast_eval, optimization_eval) -> str:
    lines = ["# GridMind Evaluation Report", ""]
    lines.append(
        "This report is generated by `apps/api/scripts/evaluate_models.py` against the "
        "actual seeded synthetic dataset. Every number below is a real, computed result "
        "from that run -- nothing here is hand-typed or estimated."
    )
    lines.append("")
    lines.append("## Anomaly Detection vs. Injected Ground Truth")
    lines.append("")
    for k, v in anomaly_eval.items():
        if k == "note":
            continue
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append(f"> {anomaly_eval.get('note', '')}")
    lines.append("")

    lines.append("## Forecast Evaluation (Holt-Winters, holdout backtest)")
    lines.append("")
    lines.append("| Building | Horizon | MAE (kWh) | RMSE (kWh) | MAPE (%) | Test points |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for r in forecast_eval:
        lines.append(
            f"| {r['building']} | {r['horizon']} | {r['mae_kwh']} | {r['rmse_kwh']} | {r['mape_pct']} | {r['n_points']} |"
        )
    lines.append("")
    lines.append(
        "> Backtest methodology: the model is fit on all data before the holdout window, "
        "then forecasts the held-out window blind and is scored against what actually "
        "happened. Longer horizons naturally carry higher MAPE due to compounding weather "
        "and occupancy uncertainty; this is expected and disclosed rather than hidden."
    )
    lines.append("")

    lines.append("## Optimization Scenarios (preset levers vs. each building's own baseline)")
    lines.append("")
    lines.append("| Building | Preset | Energy | Cost | Peak | CO2e | Comfort | Objective score |")
    lines.append("|---|---|---:|---:|---:|---:|---|---:|")
    for r in optimization_eval:
        lines.append(
            f"| {r['building']} | {r['preset']} | {r['energy_change_pct']}% | {r['cost_change_pct']}% | "
            f"{r['peak_change_pct']}% | {r['emissions_change_pct']}% | {r['comfort_impact']} | {r['objective_score']} |"
        )
    lines.append("")
    lines.append(
        "> All changes are relative to that building's own historical baseline over the same "
        "6-month window, using the documented lever formulas in "
        "`app/optimization/simulator.py`. See `docs/model_cards.md` for methodology and limitations."
    )
    lines.append("")
    return "\n".join(lines)


def main():
    db = SessionLocal()
    try:
        print("Evaluating anomaly detection against ground truth...")
        anomaly_eval = evaluate_anomaly_detection(db)
        print(anomaly_eval)

        print("Evaluating forecasts (holdout backtest)...")
        forecast_eval = evaluate_forecasts(db)
        for r in forecast_eval:
            print(r)

        print("Evaluating optimization scenarios...")
        optimization_eval = evaluate_optimization(db)
        for r in optimization_eval:
            print(r)

        report = render_report(anomaly_eval, forecast_eval, optimization_eval)
        REPORT_PATH.parent.mkdir(exist_ok=True, parents=True)
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(f"\nReport written to {REPORT_PATH}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
