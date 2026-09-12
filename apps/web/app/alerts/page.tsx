"use client";

import { useBuilding } from "@/lib/building-context";
import { useNotifications } from "@/lib/hooks";
import { apiPost } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { Badge, Card, QueryBoundary, SectionTitle } from "@/components/ui";

export default function AlertsPage() {
  const { buildingId } = useBuilding();
  const notifications = useNotifications(buildingId);
  const qc = useQueryClient();

  async function markRead(id: number) {
    await apiPost(`/api/notifications/${id}/read`);
    qc.invalidateQueries({ queryKey: ["notifications"] });
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Alert Center</h1>
      <Card>
        <SectionTitle>Alerts</SectionTitle>
        <QueryBoundary
          isLoading={notifications.isLoading}
          error={notifications.error}
          data={notifications.data}
          empty={(d) => d.length === 0}
        >
          {(rows) => (
            <ul className="space-y-2">
              {rows.map((n) => (
                <li
                  key={n.id}
                  className={`flex items-start justify-between gap-3 p-3 rounded-md border border-border ${n.is_read ? "opacity-50" : ""}`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge tone={n.severity}>{n.severity}</Badge>
                      <span className="text-sm text-gray-100">{n.title}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{n.message}</p>
                    <p className="text-[10px] text-gray-600 mt-1">{new Date(n.created_at).toLocaleString()}</p>
                  </div>
                  {!n.is_read && (
                    <button onClick={() => markRead(n.id)} className="text-[11px] text-accent shrink-0">
                      Mark read
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </QueryBoundary>
      </Card>
    </div>
  );
}
