"use client";

import { useState } from "react";
import { useBuilding } from "@/lib/building-context";
import { useForecast, useForecastEvaluation, usePeakPrediction } from "@/lib/hooks";
import { Badge, Card, QueryBoundary, SectionTitle, StatTile } from "@/components/ui";
import { ForecastChart } from "@/components/charts";

const HORIZONS = ["24h", "7d", "30d", "90d"] as const;

export default function ForecastPage() {
  const { buildingId } = useBuilding();
  const [horizon, setHorizon] = useState<(typeof HORIZONS)[number]>("24h");
  const forecast = useForecast(buildingId, horizon);
  const peak = usePeakPrediction(buildingId);
  const evaluation = useForecastEvaluation(buildingId);

  const nextPoint = forecast.data?.points[0];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Energy Forecast</h1>
        <div className="flex gap-1">
          {HORIZONS.map((h) => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              className={`text-xs px-3 py-1.5 rounded-md border ${
                horizon === h ? "border-accent text-accent" : "border-border text-gray-400"
              }`}
            >
              {h}
            </button>
          ))}
        </div>
      </div>

      {nextPoint && (
        <div className="grid grid-cols-3 gap-3">
          <StatTile label="Expected" value={`${nextPoint.expected_kwh} kWh`} />
          <StatTile label="Lower range" value={`${nextPoint.lower_kwh} kWh`} />
          <StatTile label="Upper range" value={`${nextPoint.upper_kwh} kWh`} />
        </div>
      )}

      <Card>
        <SectionTitle>Forecast ({horizon}) — {forecast.data?.method}</SectionTitle>
        <QueryBoundary isLoading={forecast.isLoading} error={forecast.error} data={forecast.data} empty={(d) => d.points.length === 0}>
          {(d) => <ForecastChart points={d.points} />}
        </QueryBoundary>
        <p className="text-[11px] text-gray-500 mt-2">
          Shaded band is an approximate 90% forecast interval derived from in-sample residual error — not a guarantee.
        </p>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <SectionTitle>Peak Demand Prediction</SectionTitle>
          <QueryBoundary isLoading={peak.isLoading} error={peak.error} data={peak.data}>
            {(p) => (
              <div className="space-y-2 text-sm">
                <Row label="Expected peak" value={`${new Date(p.expected_peak_timestamp).toLocaleString()}`} />
                <Row label="Expected demand" value={`${p.expected_peak_kw} kW`} />
                <Row label="Historical peak" value={`${p.historical_peak_kw} kW`} />
                <div className="flex justify-between items-center text-xs mt-2">
                  <span className="text-gray-500">Risk</span>
                  <Badge tone={p.risk === "HIGH" ? "HIGH" : p.risk === "MEDIUM" ? "MEDIUM" : "LOW"}>{p.risk}</Badge>
                </div>
              </div>
            )}
          </QueryBoundary>
        </Card>

        <Card>
          <SectionTitle>Forecast Evaluation (Holdout Backtest)</SectionTitle>
          <QueryBoundary isLoading={evaluation.isLoading} error={evaluation.error} data={evaluation.data} empty={(d) => d.evaluations.length === 0}>
            {(d) => (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-border">
                    <th className="py-2">Horizon</th>
                    <th>MAE</th>
                    <th>RMSE</th>
                    <th>MAPE</th>
                  </tr>
                </thead>
                <tbody>
                  {d.evaluations.map((e) => (
                    <tr key={e.horizon_label} className="border-b border-border/50">
                      <td className="py-2 text-gray-200">{e.horizon_label}</td>
                      <td className="text-gray-400">{e.mae} kWh</td>
                      <td className="text-gray-400">{e.rmse} kWh</td>
                      <td className="text-gray-400">{e.mape}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </QueryBoundary>
          <p className="text-[11px] text-gray-500 mt-2">
            Model is fit on data before the holdout window and scored against what actually happened. Longer horizons
            naturally carry higher error.
          </p>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-200">{value}</span>
    </div>
  );
}
