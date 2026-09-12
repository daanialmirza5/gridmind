"use client";

import { useState } from "react";
import { useBuilding } from "@/lib/building-context";
import { useAnomalies } from "@/lib/hooks";
import { Anomaly } from "@/lib/types";
import { Badge, Card, QueryBoundary, SectionTitle } from "@/components/ui";

const SEVERITIES = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function AnomaliesPage() {
  const { buildingId } = useBuilding();
  const [severity, setSeverity] = useState("ALL");
  const anomalies = useAnomalies(buildingId, severity === "ALL" ? undefined : severity);
  const [selected, setSelected] = useState<Anomaly | null>(null);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Energy Anomalies</h1>
        <div className="flex gap-1">
          {SEVERITIES.map((s) => (
            <button
              key={s}
              onClick={() => setSeverity(s)}
              className={`text-xs px-3 py-1.5 rounded-md border ${
                severity === s ? "border-accent text-accent" : "border-border text-gray-400"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 overflow-x-auto">
          <SectionTitle>Detected Anomalies</SectionTitle>
          <QueryBoundary isLoading={anomalies.isLoading} error={anomalies.error} data={anomalies.data} empty={(d) => d.length === 0}>
            {(rows) => (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-border">
                    <th className="py-2">Meter</th>
                    <th>Timestamp</th>
                    <th>Expected</th>
                    <th>Actual</th>
                    <th>Deviation</th>
                    <th>Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((a) => (
                    <tr
                      key={a.id}
                      onClick={() => setSelected(a)}
                      className={`border-b border-border/50 cursor-pointer hover:bg-white/5 ${
                        selected?.id === a.id ? "bg-white/5" : ""
                      }`}
                    >
                      <td className="py-2 text-gray-200">{a.meter_id}</td>
                      <td className="text-gray-400">{new Date(a.timestamp).toLocaleString()}</td>
                      <td className="text-gray-400">{a.expected_kwh} kWh</td>
                      <td className="text-gray-400">{a.actual_kwh} kWh</td>
                      <td className={a.deviation_pct > 0 ? "text-orange-400" : "text-blue-400"}>
                        {a.deviation_pct > 0 ? "+" : ""}
                        {a.deviation_pct}%
                      </td>
                      <td>
                        <Badge tone={a.severity}>{a.severity}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </QueryBoundary>
        </Card>

        <Card>
          <SectionTitle>Evidence</SectionTitle>
          {!selected && <p className="text-xs text-gray-500">Select an anomaly to inspect the evidence used to flag it.</p>}
          {selected && (
            <div className="space-y-2 text-sm">
              <Row label="Meter" value={selected.meter_id} />
              <Row label="Time range" value={new Date(selected.timestamp).toLocaleString()} />
              <Row label="Expected" value={`${selected.expected_kwh} kWh`} />
              <Row label="Actual" value={`${selected.actual_kwh} kWh`} />
              <Row label="Detection method" value={selected.detection_method} />
              <Row label="Occupancy at time" value={String((selected.evidence as any)?.operating_hour ?? "—")} />
              <div className="pt-2 border-t border-border mt-2">
                <div className="stat-label">Conclusion</div>
                <p className="text-gray-300 text-xs mt-1">{selected.probable_cause}.</p>
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
