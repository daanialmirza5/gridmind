"use client";

import { ReactNode } from "react";
import clsx from "clsx";
import { Loader2, AlertTriangle, Inbox } from "lucide-react";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("card p-4", className)}>{children}</div>;
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-300">{children}</h2>
      {action}
    </div>
  );
}

export function StatTile({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  const toneColor =
    tone === "good" ? "text-emerald-400" : tone === "warn" ? "text-amber-400" : tone === "bad" ? "text-red-400" : "text-gray-100";
  return (
    <Card>
      <div className="stat-label">{label}</div>
      <div className={clsx("text-2xl font-semibold mt-1", toneColor)}>{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </Card>
  );
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: string }) {
  const map: Record<string, string> = {
    CRITICAL: "text-red-400",
    HIGH: "text-orange-400",
    MEDIUM: "text-yellow-400",
    LOW: "text-blue-400",
    default: "text-gray-400",
    good: "text-emerald-400",
  };
  return <span className={clsx("badge", map[tone] || map.default)}>{children}</span>;
}

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  const base = "px-3 py-1.5 rounded-md text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed";
  const variants: Record<string, string> = {
    primary: "bg-accent text-black hover:brightness-110",
    secondary: "bg-transparent border border-border text-gray-200 hover:bg-white/5",
    danger: "bg-red-600/90 text-white hover:bg-red-600",
  };
  return (
    <button type={type} className={clsx(base, variants[variant])} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-gray-500 text-sm py-8 justify-center">
      <Loader2 className="animate-spin" size={16} /> {label}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 text-red-400 text-sm py-8 justify-center">
      <AlertTriangle size={16} /> {message}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 text-gray-500 text-sm py-8 justify-center">
      <Inbox size={16} /> {message}
    </div>
  );
}

export function QueryBoundary<T>({
  isLoading,
  error,
  data,
  empty,
  children,
}: {
  isLoading: boolean;
  error: unknown;
  data: T | undefined;
  empty?: (data: T) => boolean;
  children: (data: T) => ReactNode;
}) {
  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message={error instanceof Error ? error.message : "Something went wrong"} />;
  if (data === undefined) return <EmptyState message="No data available" />;
  if (empty && empty(data)) return <EmptyState message="No data available" />;
  return <>{children(data)}</>;
}
