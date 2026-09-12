"use client";

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";
import { apiPost } from "./api";

interface AuthUser {
  username: string;
  full_name: string;
  role: string;
}

interface LoginResponse extends AuthUser {
  access_token: string;
  token_type: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const raw = window.localStorage.getItem("gridmind_user");
    const token = window.localStorage.getItem("gridmind_token");
    if (raw && token) {
      try {
        setUser(JSON.parse(raw));
      } catch {
        /* ignore */
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const response = await apiPost<LoginResponse>("/api/auth/login", { username, password });
    window.localStorage.setItem("gridmind_token", response.access_token);
    const authUser = { username: response.username, full_name: response.full_name, role: response.role };
    window.localStorage.setItem("gridmind_user", JSON.stringify(authUser));
    setUser(authUser);
  }, []);

  const logout = useCallback(() => {
    window.localStorage.removeItem("gridmind_token");
    window.localStorage.removeItem("gridmind_user");
    setUser(null);
  }, []);

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
