"use client";

import { useState } from "react";
import { useBuilding } from "@/lib/building-context";
import { useCreateScenario, useSimulateScenario } from "@/lib/hooks";
import { Badge, Button, Card, SectionTitle } from "@/components/ui";
import { ComparisonBarChart } from "@/components/charts";

const OBJECTIVES = ["balanced", "cost", "energy", "emissions", "peak"];
const PRESETS = ["conservative", "balanced", "aggressive"];

export default function OptimizationPage() {
  const { buildingId } = useBuilding();
  const [setpoint, setSetpoint] = useState(2);
  const [cutback, setCutback] = useState(2);
  const [lighting, setLighting] = useState(20);
  const [peakShift, setPeakShift] = useState(5);
  const [objective, setObjective] = useState("balanced");
  const [scenarioName, setScenarioName] = useState("Custom scenario");
  const [saved, setSaved] = useState<string | null>(null);

  const simulate = useSimulateScenario();
  const create = useCreateScenario();

  function applyPreset(preset: string) {
    const presetLevers: Record<string, [number, number, number, number]> = {
      conservative: [1, 1, 10, 0],
      balanced: [2, 2, 20, 5],
      aggressive: [3, 3, 35, 15],
    };
    const [sp, cb, lt, ps] = presetLevers[preset];
    setSetpoint(sp);
    setCutback(cb);
    setLighting(lt);
    setPeakShift(ps);
    runSimulation({ hvac_setpoint_delta_c: sp, after_hours_cutback_hours: cb, lighting_reduction_pct: lt, peak_shift_kw: ps });
  }

  function runSimulation(levers?: Record<string, number>) {
    simulate.mutate({
      building_id: buildingId,
      levers: levers || {
        hvac_setpoint_delta_c: setpoint,
        after_hours_cutback_hours: cutback,
        lighting_reduction_pct: lighting,
        peak_shift_kw: peakShift,
      },
      objective,
    });
  }

  async function saveScenario() {
    await create.mutateAsync({
      building_id: buildingId,
      name: scenarioName,
      levers: {
        hvac_setpoint_delta_c: setpoint,
        after_hours_cutback_hours: cutback,
        lighting_reduction_pct: lighting,
        peak_shift_kw: peakShift,
      },
      objective,
    });
    setSaved("Scenario saved. View it under Scenarios.");
  }

  const metrics = simulate.data?.metrics;
  const chartData = metrics
    ? [
        { name: "Energy (kWh)", Baseline: metrics.baseline_energy_kwh, Scenario: metrics.scenario_energy_kwh },
        { name: "Cost ($)", Baseline: metrics.baseline_cost, Scenario: metrics.scenario_cost },
        { name: "Peak (kW)", Baseline: metrics.baseline_peak_kw, Scenario: metrics.scenario_peak_kw },
        { name: "CO2e (kg)", Baseline: metrics.baseline_emissions_kg, Scenario: metrics.scenario_emissions_kg },
      ]
    : [];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Energy Optimization Lab</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-1 space-y-4">
          <SectionTitle>Levers</SectionTitle>

          <div className="flex gap-1 mb-2">
            {PRESETS.map((p) => (
              <button key={p} onClick={() => applyPreset(p)} className="text-xs px-2 py-1 rounded-md border border-border text-gray-400 hover:text-accent hover:border-accent">
                {p}
              </button>
            ))}
          </div>

          <LeverSlider label={`HVAC setpoint: 22°C → ${(22 + setpoint).toFixed(1)}°C`} value={setpoint} min={-2} max={5} step={0.5} onChange={setSetpoint} />
          <LeverSlider label={`After-hours HVAC cutback: ${cutback}h`} value={cutback} min={0} max={4} step={1} onChange={setCutback} />
          <LeverSlider label={`Lighting reduction: ${lighting}%`} value={lighting} min={0} max={50} step={5} onChange={setLighting} />
          <LeverSlider label={`Peak load shift: ${peakShift} kW`} value={peakShift} min={0} max={20} step={1} onChange={setPeakShift} />

          <div>
            <label className="text-xs text-gray-400">Optimization objective</label>
            <select
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              className="w-full mt-1 bg-panel border border-border rounded-md px-2 py-1.5 text-sm text-gray-100"
            >
              {OBJECTIVES.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </div>

          <Button onClick={() => runSimulation()} disabled={simulate.isPending}>
            {simulate.isPending ? "Simulating…" : "Run simulation"}
          </Button>

          {simulate.data && (
            <div className="pt-3 border-t border-border space-y-2">
              <input
                value={scenarioName}
                onChange={(e) => setScenarioName(e.target.value)}
                className="w-full bg-panel border border-border rounded-md px-2 py-1.5 text-xs text-gray-100"
              />
              <Button variant="secondary" onClick={saveScenario} disabled={create.isPending}>
                {create.isPending ? "Saving…" : "Save scenario"}
              </Button>
              {saved && <p className="text-[11px] text-emerald-400">{saved}</p>}
            </div>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <SectionTitle>Baseline vs Scenario</SectionTitle>
          {simulate.isError && <p className="text-xs text-red-400">{(simulate.error as Error).message}</p>}
          {!simulate.data && !simulate.isPending && <p className="text-xs text-gray-500">Adjust levers and run a simulation.</p>}
          {metrics && (
            <>
              <ComparisonBarChart data={chartData} bars={[{ key: "Baseline", label: "Baseline", color: "#4b5563" }, { key: "Scenario", label: "Scenario", color: "#3fb6a8" }]} />
              <div className="grid grid-cols-4 gap-3 mt-4 text-center">
                <DeltaTile label="Energy" pct={metrics.energy_change_pct} />
                <DeltaTile label="Cost" pct={metrics.cost_change_pct} />
                <DeltaTile label="Peak" pct={metrics.peak_change_pct} />
                <DeltaTile label="CO2e" pct={metrics.emissions_change_pct} />
              </div>
              <div className="mt-4 flex items-center justify-between text-sm border-t border-border pt-3">
                <span className="text-gray-400">Comfort impact</span>
                <Badge tone={simulate.data!.comfort_impact === "High" ? "HIGH" : simulate.data!.comfort_impact === "Medium" ? "MEDIUM" : "good"}>
                  {simulate.data!.comfort_impact}
                </Badge>
              </div>
              <ul className="text-[11px] text-gray-500 mt-2 space-y-1">
                {simulate.data!.comfort_notes.map((n, i) => (
                  <li key={i}>• {n}</li>
                ))}
              </ul>
              <p className="text-[11px] text-gray-500 mt-3 italic">
                Estimated potential impact based on synthetic data and documented model assumptions — see docs/model_cards.md.
              </p>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}

function LeverSlider({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <label className="text-xs text-gray-400">{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full mt-1 accent-accent"
      />
    </div>
  );
}

function DeltaTile({ label, pct }: { label: string; pct: number }) {
  const improved = pct < 0;
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`text-lg font-semibold ${improved ? "text-emerald-400" : pct > 0 ? "text-red-400" : "text-gray-300"}`}>
        {pct > 0 ? "+" : ""}
        {pct}%
      </div>
    </div>
  );
}
