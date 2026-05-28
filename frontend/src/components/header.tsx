"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun, Bell, User, Menu, LogOut, Database, Loader2, PackagePlus, CheckCircle2, ArrowUpCircle } from "lucide-react";
import { useAuth } from "../contexts/auth-context";
import { api } from "../services/api";
import type { DocumentVersionEvent } from "../services/api";

const SEEN_KEY = "doc_notifications_seen_at";

function timeAgo(ts: string): string {
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 60)    return `${diff}s ago`;
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

interface HeaderProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export function Header({ sidebarOpen, setSidebarOpen }: HeaderProps) {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);

  const [versions, setVersions]     = useState<DocumentVersionEvent[]>([]);
  const [bellOpen, setBellOpen]     = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const bellRef = useRef<HTMLDivElement>(null);

  const fetchVersions = useCallback(async () => {
    try {
      const data = await api.getRecentDocumentVersions(20);
      const list = data.versions ?? [];
      setVersions(list);
      const seenAt = localStorage.getItem(SEEN_KEY);
      const cutoff = seenAt ? new Date(seenAt).getTime() : 0;
      setUnreadCount(list.filter((v) => new Date(v.ingested_at).getTime() > cutoff).length);
    } catch {
      // silently ignore — notifications are non-critical
    }
  }, []);

  useEffect(() => {
    fetchVersions();
    const id = setInterval(fetchVersions, 60_000);
    return () => clearInterval(id);
  }, [fetchVersions]);

  useEffect(() => {
    if (!bellOpen) return;
    const onClickOutside = (e: MouseEvent) => {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
        setBellOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [bellOpen]);

  const openBell = () => {
    setBellOpen((prev) => !prev);
    if (!bellOpen) {
      localStorage.setItem(SEEN_KEY, new Date().toISOString());
      setUnreadCount(0);
    }
  };

  const handleLogout = async () => {
    setLoggingOut(true);
    await logout();
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
        {namespaceLabel && (
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
            <Database className="w-3 h-3" />
            {namespaceLabel}
          </div>
        )}

        {/* Bell notification */}
        <div ref={bellRef} className="relative">
          <button
            onClick={openBell}
            className="relative p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            title="Document version notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 min-w-[14px] h-[14px] bg-destructive text-white text-[9px] font-bold rounded-full flex items-center justify-center px-0.5">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {bellOpen && (
            <div className="absolute right-0 top-full mt-2 w-80 max-h-96 overflow-y-auto rounded-xl border border-border bg-card shadow-lg z-50">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <span className="text-sm font-semibold flex items-center gap-2">
                  <PackagePlus className="h-4 w-4 text-blue-500" />
                  Document Versions
                </span>
                <span className="text-xs text-muted-foreground">{versions.length} events</span>
              </div>

              {versions.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  No documents ingested yet.
                </p>
              ) : (
                <div className="divide-y divide-border">
                  {versions.map((v, i) => (
                    <div key={`${v.doc_id}-${v.version}-${i}`} className="flex items-start gap-3 px-4 py-3 hover:bg-muted/40 transition-colors">
                      <div className="mt-0.5 shrink-0">
                        {v.is_latest ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : (
                          <ArrowUpCircle className="h-4 w-4 text-muted-foreground/40" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium truncate" title={v.source_file}>
                          {v.source_file}
                        </p>
                        <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                          <span className="text-xs text-muted-foreground capitalize">
                            {v.dept_name ?? v.dept}
                          </span>
                          <span className="text-xs font-mono bg-muted px-1 rounded">
                            {v.version}
                          </span>
                          {v.version !== "v1" && v.is_latest && (
                            <span className="text-xs text-blue-500 font-medium">NEW</span>
                          )}
                          {!v.is_latest && (
                            <span className="text-xs text-muted-foreground">superseded</span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {v.ingested_by} · {timeAgo(v.ingested_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

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
            <User className="w-4 h-4 text-primary" />
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
