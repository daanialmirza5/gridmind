"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { apiGet } from "@/lib/api";
import { Button } from "@/components/ui";

interface DemoUser {
  username: string;
  full_name: string;
  role: string;
}

export default function LoginPage() {
  const { user, login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("energy.manager");
  const [password, setPassword] = useState("gridmind-demo");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { data: demoUsers } = useQuery({
    queryKey: ["demo-users"],
    queryFn: () => apiGet<DemoUser[]>("/api/auth/demo-users"),
  });

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="w-full max-w-sm card p-6">
        <div className="text-2xl font-bold text-white mb-1">GridMind</div>
        <div className="text-sm text-gray-500 mb-6">See where energy is wasted. Predict what happens next.</div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label htmlFor="username" className="text-xs text-gray-400">Username</label>
            <input
              id="username"
              className="w-full mt-1 bg-panel border border-border rounded-md px-3 py-2 text-sm text-gray-100"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="password" className="text-xs text-gray-400">Password</label>
            <input
              id="password"
              type="password"
              className="w-full mt-1 bg-panel border border-border rounded-md px-3 py-2 text-sm text-gray-100"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <div className="text-xs text-red-400">{error}</div>}
          <Button type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        {demoUsers && demoUsers.length > 0 && (
          <div className="mt-6 pt-4 border-t border-border">
            <div className="text-xs text-gray-500 mb-2">Demo accounts (password: gridmind-demo)</div>
            <div className="flex flex-wrap gap-1.5">
              {demoUsers.map((u) => (
                <button
                  key={u.username}
                  onClick={() => setUsername(u.username)}
                  className="text-[11px] px-2 py-1 rounded-md border border-border text-gray-400 hover:text-gray-200 hover:bg-white/5"
                >
                  {u.role}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
