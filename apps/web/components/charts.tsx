"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { EnergyPoint, ForecastPoint } from "@/lib/types";

const AXIS_COLOR = "#7c8794";
const GRID_COLOR = "#232a35";

function formatTs(ts: string) {
  const d = new Date(ts);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:00`;
}

export function EnergyTrendChart({ points }: { points: EnergyPoint[] }) {
  const data = points.map((p) => ({ ...p, label: formatTs(p.timestamp) }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="energyFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3fb6a8" stopOpacity={0.4} />
            <stop offset="100%" stopColor="#3fb6a8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" stroke={AXIS_COLOR} fontSize={11} tickLine={false} minTickGap={40} />
        <YAxis stroke={AXIS_COLOR} fontSize={11} tickLine={false} width={50} />
        <Tooltip
          contentStyle={{ background: "#12161c", border: "1px solid #232a35", fontSize: 12 }}
          labelStyle={{ color: "#d7dce2" }}
        />
        <Area type="monotone" dataKey="energy_kwh" name="Energy (kWh)" stroke="#3fb6a8" fill="url(#energyFill)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ForecastChart({ points }: { points: ForecastPoint[] }) {
  const data = points.map((p) => ({
    label: formatTs(p.timestamp),
    expected_kwh: p.expected_kwh,
    lower_kwh: p.lower_kwh,
    band: Math.max(p.upper_kwh - p.lower_kwh, 0),
  }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data}>
        <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" stroke={AXIS_COLOR} fontSize={11} tickLine={false} minTickGap={40} />
        <YAxis stroke={AXIS_COLOR} fontSize={11} tickLine={false} width={50} />
        <Tooltip contentStyle={{ background: "#12161c", border: "1px solid #232a35", fontSize: 12 }} />
        <Area type="monotone" dataKey="lower_kwh" stackId="band" stroke="none" fill="transparent" name="Lower bound" />
        <Area
          type="monotone"
          dataKey="band"
          stackId="band"
          stroke="none"
          fill="#3fb6a8"
          fillOpacity={0.15}
          name="Forecast interval"
        />
        <Line type="monotone" dataKey="expected_kwh" stroke="#3fb6a8" strokeWidth={2} dot={false} name="Expected (kWh)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ComparisonBarChart({
  data,
  bars,
}: {
  data: Record<string, string | number>[];
  bars: { key: string; label: string; color: string }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="name" stroke={AXIS_COLOR} fontSize={11} tickLine={false} />
        <YAxis stroke={AXIS_COLOR} fontSize={11} tickLine={false} />
        <Tooltip contentStyle={{ background: "#12161c", border: "1px solid #232a35", fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {bars.map((b) => (
          <Bar key={b.key} dataKey={b.key} name={b.label} fill={b.color} radius={[3, 3, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function SimpleLineChart({
  data,
  dataKey,
  color = "#3fb6a8",
}: {
  data: Record<string, string | number>[];
  dataKey: string;
  color?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" stroke={AXIS_COLOR} fontSize={11} tickLine={false} minTickGap={40} />
        <YAxis stroke={AXIS_COLOR} fontSize={11} tickLine={false} width={50} />
        <Tooltip contentStyle={{ background: "#12161c", border: "1px solid #232a35", fontSize: 12 }} />
        <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
