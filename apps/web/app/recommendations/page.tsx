"use client";

import { useState } from "react";
import { useBuilding } from "@/lib/building-context";
import { useDecideRecommendation, useRecommendations } from "@/lib/hooks";
import { Badge, Button, Card, QueryBoundary } from "@/components/ui";

const STATUS_FILTERS = ["ALL", "SUGGESTED", "APPROVED", "REJECTED", "IMPLEMENTED"];

export default function RecommendationsPage() {
  const { buildingId } = useBuilding();
  const [status, setStatus] = useState("ALL");
  const recs = useRecommendations(buildingId, status === "ALL" ? undefined : status);
  const decide = useDecideRecommendation();
  const [reason, setReason] = useState<Record<string, string>>({});

  const sorted = [...(recs.data || [])].sort((a, b) => b.priority_score - a.priority_score);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Recommendations</h1>
        <div className="flex gap-1">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={`text-xs px-3 py-1.5 rounded-md border ${status === s ? "border-accent text-accent" : "border-border text-gray-400"}`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <QueryBoundary isLoading={recs.isLoading} error={recs.error} data={sorted} empty={(d) => d.length === 0}>
        {(rows) => (
          <div className="space-y-3">
            {rows.map((r, i) => (
              <Card key={r.id}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500 text-xs">#{i + 1}</span>
                      <h3 className="text-white font-medium">{r.title}</h3>
                      <Badge tone={statusTone(r.status)}>{r.status}</Badge>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">{r.description}</p>
                    <div className="flex gap-4 mt-2 text-xs text-gray-500">
                      <span>Effort: {r.effort}</span>
                      <span>Confidence: {r.confidence}</span>
                      <span>Priority: {r.priority_score}</span>
                    </div>
                    <div className="flex gap-4 mt-2 text-sm">
                      <span className="text-emerald-400">-{r.estimated_energy_savings_kwh} kWh</span>
                      <span className="text-emerald-400">-${r.estimated_cost_savings}</span>
                      <span className="text-emerald-400">-{r.estimated_emissions_reduction_kg} kg CO2e</span>
                    </div>
                    <p className="text-[11px] text-gray-600 italic mt-1">{r.disclaimer}</p>
                  </div>

                  {r.status === "SUGGESTED" && (
                    <div className="w-56 shrink-0 space-y-2">
                      <input
                        placeholder="Reason (optional)"
                        value={reason[r.id] || ""}
                        onChange={(e) => setReason((prev) => ({ ...prev, [r.id]: e.target.value }))}
                        className="w-full bg-panel border border-border rounded-md px-2 py-1 text-xs text-gray-100"
                      />
                      <div className="flex gap-2">
                        <Button onClick={() => decide.mutate({ id: r.id, action: "approve", reason: reason[r.id] || "" })}>
                          Approve
                        </Button>
                        <Button
                          variant="danger"
                          onClick={() => decide.mutate({ id: r.id, action: "reject", reason: reason[r.id] || "" })}
                        >
                          Reject
                        </Button>
                      </div>
                    </div>
                  )}
                  {r.status === "APPROVED" && (
                    <Button variant="secondary" onClick={() => decide.mutate({ id: r.id, action: "implement", reason: "" })}>
                      Mark implemented
                    </Button>
                  )}
                </div>
                {r.decided_by && (
                  <p className="text-[11px] text-gray-600 mt-2 border-t border-border pt-2">
                    Decided by {r.decided_by} {r.decided_at && `on ${new Date(r.decided_at).toLocaleString()}`}
                    {r.decision_reason && ` — "${r.decision_reason}"`}
                  </p>
                )}
              </Card>
            ))}
          </div>
        )}
      </QueryBoundary>
    </div>
  );
}

function statusTone(status: string) {
  if (status === "APPROVED" || status === "IMPLEMENTED") return "good";
  if (status === "REJECTED") return "HIGH";
  return "default";
}
