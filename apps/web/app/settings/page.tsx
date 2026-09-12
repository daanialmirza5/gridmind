"use client";

import { useAuth } from "@/lib/auth";
import { useSystemHealth } from "@/lib/hooks";
import { Card, QueryBoundary, SectionTitle } from "@/components/ui";

export default function SettingsPage() {
  const { user } = useAuth();
  const health = useSystemHealth();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Settings</h1>

      <Card>
        <SectionTitle>Account</SectionTitle>
        <div className="text-sm space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Username</span>
            <span className="text-gray-200">{user?.username}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Full name</span>
            <span className="text-gray-200">{user?.full_name}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Role</span>
            <span className="text-gray-200">{user?.role}</span>
          </div>
        </div>
      </Card>

      <Card>
        <SectionTitle>System</SectionTitle>
        <QueryBoundary isLoading={health.isLoading} error={health.error} data={health.data}>
          {(d) => (
            <div className="text-sm space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Environment</span>
                <span className="text-gray-200">{d.environment}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">AI provider</span>
                <span className="text-gray-200">{d.ai_provider_configured}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Database</span>
                <span className="text-gray-200">{d.database}</span>
              </div>
            </div>
          )}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionTitle>Role Permissions</SectionTitle>
        <ul className="text-xs text-gray-400 space-y-1">
          <li><span className="text-gray-200">ENERGY_MANAGER</span> — full operational analytics, approve/reject recommendations, run detections</li>
          <li><span className="text-gray-200">FACILITY_MANAGER</span> — building/asset operations, approve/reject recommendations</li>
          <li><span className="text-gray-200">ANALYST</span> — analytics, scenarios, run detections</li>
          <li><span className="text-gray-200">EXECUTIVE</span> — read-only strategic dashboards</li>
          <li><span className="text-gray-200">ADMIN</span> — full system configuration</li>
        </ul>
      </Card>
    </div>
  );
}
