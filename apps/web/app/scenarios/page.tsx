"use client";

import Link from "next/link";
import { useBuilding } from "@/lib/building-context";
import { useScenarios } from "@/lib/hooks";
import { Badge, Card, QueryBoundary, SectionTitle } from "@/components/ui";

export default function ScenariosPage() {
  const { buildingId } = useBuilding();
  const scenarios = useScenarios(buildingId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Scenario Comparison</h1>
        <Link href="/optimization" className="text-xs text-accent">
          + New scenario
        </Link>
      </div>

      <Card className="overflow-x-auto">
        <SectionTitle>Saved Scenarios</SectionTitle>
        <QueryBoundary isLoading={scenarios.isLoading} error={scenarios.error} data={scenarios.data} empty={(d) => d.length === 0}>
          {(rows) => (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 border-b border-border">
                  <th className="py-2">Name</th>
                  <th>Objective</th>
                  <th>Energy Δ</th>
                  <th>Cost Δ</th>
                  <th>Comfort</th>
                  <th>Objective score</th>
                  <th>Created by</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr key={s.id} className="border-b border-border/50">
                    <td className="py-2 text-gray-200">{s.name}</td>
                    <td className="text-gray-400">{s.objective}</td>
                    <td className={pctColor(s.result?.energy_change_pct)}>{fmtPct(s.result?.energy_change_pct)}</td>
                    <td className={pctColor(s.result?.cost_change_pct)}>{fmtPct(s.result?.cost_change_pct)}</td>
                    <td>
                      {s.result?.comfort_impact ? (
                        <Badge tone={s.result.comfort_impact === "High" ? "HIGH" : s.result.comfort_impact === "Medium" ? "MEDIUM" : "good"}>
                          {s.result.comfort_impact}
                        </Badge>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="text-gray-400">{s.result?.objective_score ?? "—"}</td>
                    <td className="text-gray-500">{s.created_by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </QueryBoundary>
      </Card>
    </div>
  );
}

function fmtPct(v: number | null | undefined) {
  if (v === null || v === undefined) return "—";
  return `${v > 0 ? "+" : ""}${v}%`;
}
function pctColor(v: number | null | undefined) {
  if (v === null || v === undefined) return "text-gray-400";
  return v < 0 ? "text-emerald-400" : v > 0 ? "text-red-400" : "text-gray-300";
}
