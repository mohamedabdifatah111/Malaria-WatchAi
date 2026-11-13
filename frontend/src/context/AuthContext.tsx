import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { setUnauthorizedHandler, tokenStore } from "../api/client";
import { login as apiLogin } from "../api/endpoints";

interface AuthState {
  isAuthenticated: boolean;
  /** Set when the backend rejected the stored token (401). */
  sessionExpired: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * Token authentication against POST /api/v1/auth/token/.
 * Roles are NOT inferred here: permission checks are the backend's job, and the
 * UI never treats a client-side flag as proof of reviewer rights.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [isAuthenticated, setAuthenticated] = useState(() => Boolean(tokenStore.get()));
  const [sessionExpired, setSessionExpired] = useState(false);

  const logout = useCallback(() => {
    tokenStore.clear();
    setAuthenticated(false);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSessionExpired(true);
      setAuthenticated(false);
      queryClient.clear();
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient]);

  const login = useCallback(async (username: string, password: string) => {
    const token = await apiLogin(username, password);
    tokenStore.set(token);
    setSessionExpired(false);
    setAuthenticated(true);
  }, []);

  const value = useMemo(() => ({ isAuthenticated, sessionExpired, login, logout }),
    [isAuthenticated, sessionExpired, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
