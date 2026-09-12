"use client";

import { useState } from "react";
import { useBuilding } from "@/lib/building-context";
import { useWasteEvents } from "@/lib/hooks";
import { WasteEvent } from "@/lib/types";
import { Badge, Card, QueryBoundary, SectionTitle } from "@/components/ui";

export default function WastePage() {
  const { buildingId } = useBuilding();
  const waste = useWasteEvents(buildingId);
  const [selected, setSelected] = useState<WasteEvent | null>(null);

  const totalKwh = (waste.data || []).reduce((s, w) => s + w.estimated_waste_kwh, 0);
  const totalCost = (waste.data || []).reduce((s, w) => s + w.estimated_cost, 0);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Waste Detection</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <div className="stat-label">Events</div>
          <div className="text-2xl font-semibold text-gray-100">{waste.data?.length ?? "—"}</div>
        </Card>
        <Card>
          <div className="stat-label">Estimated waste</div>
          <div className="text-2xl font-semibold text-amber-400">{totalKwh.toFixed(0)} kWh</div>
        </Card>
        <Card>
          <div className="stat-label">Estimated cost</div>
          <div className="text-2xl font-semibold text-amber-400">${totalCost.toFixed(0)}</div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 overflow-x-auto">
          <SectionTitle>Waste Events</SectionTitle>
          <QueryBoundary isLoading={waste.isLoading} error={waste.error} data={waste.data} empty={(d) => d.length === 0}>
            {(rows) => (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-border">
                    <th className="py-2">Rule</th>
                    <th>Window</th>
                    <th>Waste (kWh)</th>
                    <th>Cost</th>
                    <th>Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((w) => (
                    <tr
                      key={w.id}
                      onClick={() => setSelected(w)}
                      className={`border-b border-border/50 cursor-pointer hover:bg-white/5 ${
                        selected?.id === w.id ? "bg-white/5" : ""
                      }`}
                    >
                      <td className="py-2 text-gray-200">{w.rule.replace(/_/g, " ")}</td>
                      <td className="text-gray-400">
                        {new Date(w.window_start).toLocaleString()} — {new Date(w.window_end).toLocaleTimeString()}
                      </td>
                      <td className="text-gray-400">{w.estimated_waste_kwh}</td>
                      <td className="text-gray-400">${w.estimated_cost}</td>
                      <td>
                        <Badge tone={w.severity}>{w.severity}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </QueryBoundary>
        </Card>

        <Card>
          <SectionTitle>Why was this flagged?</SectionTitle>
          {!selected && <p className="text-xs text-gray-500">Select a waste event to see the triggering evidence.</p>}
          {selected && (
            <div className="space-y-2 text-sm">
              <Row label="Meter" value={selected.meter_id} />
              <Row label="Zone" value={selected.zone_id || "building-level"} />
              <Row label="Window" value={`${new Date(selected.window_start).toLocaleString()} – ${new Date(selected.window_end).toLocaleTimeString()}`} />
              <Row label="Estimated waste" value={`${selected.estimated_waste_kwh} kWh`} />
              <Row label="Estimated cost" value={`$${selected.estimated_cost}`} />
              <Row label="Estimated CO2e" value={`${selected.estimated_emissions_kg} kg`} />
              <div className="pt-2 border-t border-border mt-2">
                <div className="stat-label">Rule</div>
                <p className="text-gray-300 text-xs mt-1">{String((selected.evidence as any)?.rule || selected.rule)}</p>
              </div>
              <pre className="text-[10px] text-gray-500 bg-black/30 rounded p-2 mt-2 overflow-x-auto">
                {JSON.stringify(selected.evidence, null, 2)}
              </pre>
            </div>
          )}
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
