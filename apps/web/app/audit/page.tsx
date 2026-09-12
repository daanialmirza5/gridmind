"use client";

import { useAuditEvents } from "@/lib/hooks";
import { Card, QueryBoundary, SectionTitle } from "@/components/ui";

export default function AuditPage() {
  const audit = useAuditEvents();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Audit Trail</h1>
      <Card className="overflow-x-auto">
        <SectionTitle>Recent System Events</SectionTitle>
        <QueryBoundary isLoading={audit.isLoading} error={audit.error} data={audit.data} empty={(d) => d.length === 0}>
          {(rows) => (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 border-b border-border">
                  <th className="py-2">Time</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Entity</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.id} className="border-b border-border/50">
                    <td className="py-2 text-gray-400">{new Date(e.timestamp).toLocaleString()}</td>
                    <td className="text-gray-200">{e.actor}</td>
                    <td className="text-gray-300">{e.action}</td>
                    <td className="text-gray-400">
                      {e.entity_type}:{e.entity_id}
                    </td>
                    <td className="text-gray-500">{e.reason || "—"}</td>
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
