"use client";

import { createContext, useContext, useEffect, useRef, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api } from "../services/api";
import type { UserRole } from "../services/api";

function getBackendBase(): string {
  if (typeof window === "undefined") return "http://localhost:8004";
  const hostname = window.location.hostname;
  if (hostname.includes("azurecontainerapps.io")) {
    return `https://${hostname.replace("huron-dev-frontend", "huron-dev-backend")}`;
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8004";
}

// Re-validate the token every 5 minutes while the app is open.
const REVALIDATE_INTERVAL_MS = 5 * 60 * 1000;

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  department: string;
  role: UserRole;
  permissions: string[];
  namespace_scope?: string[];
  avatar?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  sessionExpiresAt: Date | null;
  login: (token: string, user: User) => void;
  loginWithToken: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  hasRole: (roles: string[]) => boolean;
  isRoot: () => boolean;
  isDeptAdmin: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Decode the JWT exp claim without verifying the signature.
// We trust the backend already validated it — we just need the timestamp.
function getTokenExpiryDate(token: string): Date | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp ? new Date(payload.exp * 1000) : null;
  } catch {
    return null;
  }
}

function clearSession() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("user");
  localStorage.removeItem("mfa_verified");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]                     = useState<User | null>(null);
  const [isLoading, setIsLoading]           = useState(true);
  const [sessionExpiresAt, setSessionExpiresAt] = useState<Date | null>(null);
  const router                              = useRouter();

  const autoLogoutTimer  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const revalidateTimer  = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimers = () => {
    if (autoLogoutTimer.current)  clearTimeout(autoLogoutTimer.current);
    if (revalidateTimer.current)  clearInterval(revalidateTimer.current);
  };

  const logout = async () => {
    clearTimers();
    clearSession();
    setUser(null);
    setSessionExpiresAt(null);
    await api.logout().catch(() => {});
    router.push("/");
  };

  // Schedule automatic logout when the JWT exp arrives.
  const scheduleAutoLogout = (token: string) => {
    clearTimers();
    const expiry = getTokenExpiryDate(token);
    if (!expiry) return;

    setSessionExpiresAt(expiry);

    const msUntilExpiry = expiry.getTime() - Date.now();
    if (msUntilExpiry <= 0) {
      // Already expired — log out immediately.
      logout();
      return;
    }

    // Logout exactly when the token expires.
    autoLogoutTimer.current = setTimeout(() => {
      clearSession();
      setUser(null);
      setSessionExpiresAt(null);
      router.push("/?reason=session_expired");
    }, msUntilExpiry);
  };

  // Periodically re-validate the token with the backend while the tab is open.
  const startRevalidation = () => {
    if (revalidateTimer.current) clearInterval(revalidateTimer.current);
    revalidateTimer.current = setInterval(async () => {
      const token = localStorage.getItem("auth_token");
      if (!token) { logout(); return; }
      try {
        const response = await fetch(`${getBackendBase()}/api/v1/auth/validate`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          // Backend says token is invalid or expired — log out now.
          logout();
        }
      } catch {
        // Network error — backend unreachable. Keep the session alive;
        // the auto-logout timer will still fire when exp is reached.
      }
    }, REVALIDATE_INTERVAL_MS);
  };

  // On mount: check localStorage and validate with the backend.
  useEffect(() => {
    const checkAuth = async () => {
      const token     = localStorage.getItem("auth_token");
      const savedUser = localStorage.getItem("user");

      if (!token || !savedUser) {
        setIsLoading(false);
        return;
      }

      // Reject the token immediately if it is already past its exp claim.
      const expiry = getTokenExpiryDate(token);
      if (expiry && expiry.getTime() < Date.now()) {
        clearSession();
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(`${getBackendBase()}/api/v1/auth/validate`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (response.ok) {
          const parsed = JSON.parse(savedUser) as User;
          setUser(parsed);
          scheduleAutoLogout(token);
          startRevalidation();
        } else {
          // 401 or other error from the backend — token is invalid.
          clearSession();
        }
      } catch {
        // Backend unreachable on startup. Keep the user from localStorage
        // but schedule the auto-logout so they cannot stay past exp.
        if (expiry && expiry.getTime() > Date.now()) {
          const parsed = JSON.parse(savedUser) as User;
          setUser(parsed);
          scheduleAutoLogout(token);
        } else {
          clearSession();
        }
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
    return () => clearTimers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = (token: string, userData: User) => {
    localStorage.setItem("auth_token", token);
    localStorage.setItem("user", JSON.stringify(userData));
    setUser(userData);
    scheduleAutoLogout(token);
    startRevalidation();
  };

  // Used by SSO flow — receives token from redirect, fetches user profile
  const loginWithToken = async (token: string): Promise<void> => {
    localStorage.setItem("auth_token", token);
    const response = await fetch(`${getBackendBase()}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error("Failed to fetch user profile");
    const userData = (await response.json()) as User;
    localStorage.setItem("user", JSON.stringify(userData));
    setUser(userData);
    scheduleAutoLogout(token);
    startRevalidation();
  };

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    if (user.role === "root") return true;
    return user.permissions.includes(permission);
  };

  const hasRole = (roles: string[]): boolean => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  const isRoot      = () => user?.role === "root";
  const isDeptAdmin = () => user?.role === "root" || user?.role === "dept_admin";

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        sessionExpiresAt,
        login,
        loginWithToken,
        logout,
        hasPermission,
        hasRole,
        isRoot,
        isDeptAdmin,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
