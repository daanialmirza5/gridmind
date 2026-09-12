"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Building2,
  Boxes,
  Zap,
  AlertTriangle,
  Trash2,
  TrendingUp,
  SlidersHorizontal,
  FlaskConical,
  ClipboardList,
  Leaf,
  DollarSign,
  History,
  Share2,
  Bot,
  Bell,
  FileClock,
  Settings,
  LogOut,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useBuilding } from "@/lib/building-context";

const NAV = [
  { href: "/dashboard", label: "Command Center", icon: LayoutDashboard },
  { href: "/buildings", label: "Buildings", icon: Building2 },
  { href: "/assets", label: "Assets", icon: Boxes },
  { href: "/energy", label: "Energy", icon: Zap },
  { href: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { href: "/waste", label: "Waste", icon: Trash2 },
  { href: "/forecast", label: "Forecast", icon: TrendingUp },
  { href: "/optimization", label: "Optimization Lab", icon: SlidersHorizontal },
  { href: "/scenarios", label: "Scenarios", icon: FlaskConical },
  { href: "/recommendations", label: "Recommendations", icon: ClipboardList },
  { href: "/carbon", label: "Carbon", icon: Leaf },
  { href: "/cost", label: "Cost", icon: DollarSign },
  { href: "/replay", label: "Energy Replay", icon: History },
  { href: "/energy-flow", label: "Energy Flow", icon: Share2 },
  { href: "/ai-analyst", label: "AI Analyst", icon: Bot },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/audit", label: "Audit", icon: FileClock },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Shell({ children }: { children: ReactNode }) {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();

  if (loading) return null;

  if (!user || pathname === "/login") {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-border bg-panel flex flex-col">
        <div className="px-4 py-4 border-b border-border">
          <div className="text-lg font-bold tracking-tight text-white">GridMind</div>
          <div className="text-[11px] text-gray-500">Energy Operations Center</div>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 px-4 py-2 text-sm border-l-2 ${
                  active
                    ? "border-accent text-white bg-white/5"
                    : "border-transparent text-gray-400 hover:text-gray-200 hover:bg-white/5"
                }`}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-border p-3">
          <div className="text-xs text-gray-300">{user.full_name}</div>
          <div className="text-[11px] text-gray-500 mb-2">{user.role}</div>
          <button onClick={logout} className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-red-400">
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-6 overflow-x-hidden">{children}</main>
      </div>
    </div>
  );
}

function TopBar() {
  const { buildings, buildingId, setBuildingId, isLoading } = useBuilding();
  return (
    <header className="h-14 border-b border-border flex items-center justify-between px-6 bg-surface/60 backdrop-blur">
      <div className="text-xs text-gray-500">Synthetic demonstration dataset — no real building is connected.</div>
      {!isLoading && buildings.length > 0 && (
        <select
          value={buildingId}
          onChange={(e) => setBuildingId(e.target.value)}
          className="bg-panel border border-border rounded-md text-sm px-2 py-1.5 text-gray-200"
        >
          {buildings.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
      )}
    </header>
  );
}
