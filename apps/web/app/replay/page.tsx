"use client";

import { useState } from "react";
import { useBuilding } from "@/lib/building-context";
import { useReplay } from "@/lib/hooks";
import { Card, QueryBoundary, SectionTitle } from "@/components/ui";

export default function ReplayPage() {
  const { buildingId } = useBuilding();
  const [date, setDate] = useState("2026-07-22");
  const [hour, setHour] = useState(20);

  const timestamp = `${date}T${String(hour).padStart(2, "0")}:00:00`;
  const replay = useReplay(buildingId, timestamp);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Energy Replay</h1>
      <p className="text-sm text-gray-500">Step back to any hour in the synthetic dataset and inspect what was happening.</p>

      <Card>
        <div className="flex items-center gap-4 mb-4">
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="bg-panel border border-border rounded-md px-2 py-1.5 text-sm text-gray-100"
            min="2026-03-13"
            max="2026-09-10"
          />
          <div className="text-sm text-gray-300 font-mono">{String(hour).padStart(2, "0")}:00</div>
        </div>
        <input
          type="range"
          min={0}
          max={23}
          value={hour}
          onChange={(e) => setHour(Number(e.target.value))}
          className="w-full accent-accent"
        />
        <div className="flex justify-between text-[10px] text-gray-600 mt-1">
          {Array.from({ length: 24 }, (_, i) => (
            <span key={i}>{i % 3 === 0 ? String(i).padStart(2, "0") : ""}</span>
          ))}
        </div>
      </Card>

      <QueryBoundary isLoading={replay.isLoading} error={replay.error} data={replay.data}>
        {(snapshot) => (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card>
              <SectionTitle>Building State</SectionTitle>
              <div className="space-y-2 text-sm">
                <Row label="Timestamp" value={new Date(snapshot.timestamp).toLocaleString()} />
                <Row label="Outdoor temperature" value={`${snapshot.temperature_c ?? "—"} °C`} />
                <Row label="Main power" value={`${snapshot.main_power_kw ?? "—"} kW`} />
              </div>
            </Card>
            <Card className="lg:col-span-2 overflow-x-auto">
              <SectionTitle>Zone Snapshot</SectionTitle>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-border">
                    <th className="py-2">Zone</th>
                    <th>Power (kW)</th>
                    <th>Occupancy</th>
                    <th>State</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshot.zones.map((z) => (
                    <tr key={z.meter_id} className="border-b border-border/50">
                      <td className="py-2 text-gray-200">{z.zone_id}</td>
                      <td className="text-gray-400">{z.power_kw}</td>
                      <td className="text-gray-400">{z.occupancy ?? "—"}</td>
                      <td className="text-gray-400">{z.operating_state}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        )}
      </QueryBoundary>
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
