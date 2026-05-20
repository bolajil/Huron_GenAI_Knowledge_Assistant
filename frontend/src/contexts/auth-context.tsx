"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api } from "../services/api";
import type { UserRole } from "../services/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  login: (token: string, user: User) => void;
  logout: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  hasRole: (roles: string[]) => boolean;
  isRoot: () => boolean;
  isDeptAdmin: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem("auth_token");
        const savedUser = localStorage.getItem("user");

        if (token && savedUser) {
          const response = await fetch(`${API_BASE_URL}/api/v1/auth/validate`, {
            headers: { Authorization: `Bearer ${token}` },
          });

          if (response.ok) {
            setUser(JSON.parse(savedUser));
          } else {
            localStorage.removeItem("auth_token");
            localStorage.removeItem("user");
            localStorage.removeItem("mfa_verified");
          }
        }
      } catch {
        const savedUser = localStorage.getItem("user");
        if (savedUser) {
          setUser(JSON.parse(savedUser));
        }
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = (token: string, userData: User) => {
    localStorage.setItem("auth_token", token);
    localStorage.setItem("user", JSON.stringify(userData));
    setUser(userData);
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
    router.push("/");
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

  const isRoot = () => user?.role === "root";

  const isDeptAdmin = () =>
    user?.role === "root" || user?.role === "dept_admin";

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
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
