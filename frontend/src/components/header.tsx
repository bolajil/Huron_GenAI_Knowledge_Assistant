"use client";

import { useState } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun, Bell, User, Menu, LogOut, Database, Loader2 } from "lucide-react";
import { useAuth } from "../contexts/auth-context";

interface HeaderProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export function Header({ sidebarOpen, setSidebarOpen }: HeaderProps) {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    await logout();
    // logout() redirects to "/" so no further state cleanup needed
  };

  const namespaceLabel =
    user?.role === "root"
      ? "all namespaces"
      : user?.department
      ? `ns: ${user.department}`
      : null;

  return (
    <header className="flex items-center justify-between h-16 px-6 border-b border-border bg-card">
      {/* Left: mobile menu toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden p-2 rounded-lg hover:bg-accent"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Center: Search */}
      <div className="hidden md:flex flex-1 max-w-md mx-8">
        <input
          type="text"
          placeholder="Search documents, policies…"
          className="w-full px-4 py-2 text-sm bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-2">
        {/* Pinecone namespace badge */}
        {namespaceLabel && (
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
            <Database className="w-3 h-3" />
            {namespaceLabel}
          </div>
        )}

        {/* Notifications */}
        <button className="relative p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-destructive rounded-full" />
        </button>

        {/* Theme toggle */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        >
          {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        {/* User info */}
        <div className="flex items-center gap-2 p-2 rounded-lg hover:bg-accent">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
            {user?.avatar ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={user.avatar} alt={user.full_name} className="w-8 h-8 rounded-full" />
            ) : (
              <User className="w-4 h-4 text-primary" />
            )}
          </div>
          <div className="hidden md:block text-left">
            <p className="text-sm font-medium">{user?.full_name || "User"}</p>
            <p className="text-xs text-muted-foreground capitalize">
              {user?.department || "—"}
            </p>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          disabled={loggingOut}
          className="p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-destructive disabled:opacity-50 transition-colors"
          title="Logout"
        >
          {loggingOut ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <LogOut className="w-5 h-5" />
          )}
        </button>
      </div>
    </header>
  );
}
