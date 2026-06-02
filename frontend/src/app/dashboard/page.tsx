"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  FileText,
  MessageSquare,
  Users,
  Clock,
  ArrowUpRight,
  Building2,
  RefreshCw,
  Zap,
  TrendingUp,
} from "lucide-react";
import { useAuth } from "../../contexts/auth-context";
import { api } from "../../services/api";
import type { StatsResponse, RecentQuery } from "../../services/api";

const REFRESH_INTERVAL_MS = 30_000;

function formatResponseTime(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
}

function timeAgo(timestamp: string): string {
  const diff = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

const STAT_CONFIG = [
  { key: "total_documents", name: "Total Documents", icon: FileText,  accent: "from-blue-500 to-cyan-400",  iconBg: "bg-blue-500/10 dark:bg-blue-500/20",  iconColor: "text-blue-500" },
  { key: "queries_today",   name: "Queries Today",   icon: MessageSquare, accent: "from-emerald-500 to-teal-400", iconBg: "bg-emerald-500/10 dark:bg-emerald-500/20", iconColor: "text-emerald-500" },
  { key: "active_users",    name: "Active Users",    icon: Users,    accent: "from-violet-500 to-purple-400", iconBg: "bg-violet-500/10 dark:bg-violet-500/20",  iconColor: "text-violet-500" },
  { key: "avg_response",    name: "Avg Response",    icon: Clock,    accent: "from-orange-500 to-amber-400",  iconBg: "bg-orange-500/10 dark:bg-orange-500/20",  iconColor: "text-orange-500" },
] as const;

const DEPT_BADGE: Record<string, string> = {
  hr:         "bg-blue-100   text-blue-700   dark:bg-blue-500/20   dark:text-blue-300",
  legal:      "bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300",
  finance:    "bg-green-100  text-green-700  dark:bg-green-500/20  dark:text-green-300",
  clinical:   "bg-red-100    text-red-700    dark:bg-red-500/20    dark:text-red-300",
  operations: "bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300",
  it:         "bg-cyan-100   text-cyan-700   dark:bg-cyan-500/20   dark:text-cyan-300",
  marketing:  "bg-pink-100   text-pink-700   dark:bg-pink-500/20   dark:text-pink-300",
  external:   "bg-slate-100  text-slate-700  dark:bg-slate-500/20  dark:text-slate-300",
  general:    "bg-slate-100  text-slate-600  dark:bg-slate-500/20  dark:text-slate-300",
};

export default function DashboardPage() {
  const { user, isRoot } = useAuth();
  const router = useRouter();
  const firstName = user?.full_name?.split(" ")[0] || "User";

  const [stats, setStats]               = useState<StatsResponse | null>(null);
  const [queries, setQueries]           = useState<RecentQuery[]>([]);
  const [loading, setLoading]           = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsData, queriesData] = await Promise.allSettled([
        api.getStats(),
        api.getRecentQueries(8),
      ]);
      if (statsData.status   === "fulfilled") setStats(statsData.value);
      if (queriesData.status === "fulfilled") setQueries(queriesData.value.queries ?? []);
      setLastRefreshed(new Date());
    } catch { /* keep stale data */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [fetchData]);

  const statValues = stats
    ? [
        stats.total_documents.toLocaleString(),
        stats.queries_today.toLocaleString(),
        stats.active_users.toLocaleString(),
        formatResponseTime(stats.avg_response_time),
      ]
    : ["—", "—", "—", "—"];

  const visibleQueries = queries.filter(
    (q) => isRoot() || q.department === user?.department
  );

  return (
    /* ── page shell — subtle mesh gradient background in light, dark stays as-is ── */
    <div className="min-h-full space-y-8 relative">

      {/* Light-mode background — soft blue-gray tint so white cards stand out */}
      <div className="pointer-events-none fixed inset-0 -z-10 dark:hidden"
        style={{
          background: "radial-gradient(ellipse 90% 60% at 15% -10%, rgba(99,102,241,0.12) 0%, transparent 55%), radial-gradient(ellipse 70% 50% at 85% 110%, rgba(6,182,212,0.10) 0%, transparent 55%), #eef0f7"
        }}
      />

      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-slate-800 via-violet-700 to-cyan-600 bg-clip-text text-transparent dark:from-white dark:via-cyan-300 dark:to-blue-400">
            Dashboard
          </h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Welcome back, <span className="font-medium text-foreground">{firstName}</span>!{" "}
            {isRoot()
              ? "Global overview — all departments."
              : `${user?.department?.toUpperCase()} department overview.`}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
          {lastRefreshed && <span>Updated {timeAgo(lastRefreshed.toISOString())}</span>}
          <button
            onClick={fetchData}
            className="p-1.5 rounded-lg hover:bg-white/60 dark:hover:bg-white/10 border border-transparent hover:border-border transition-all"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CONFIG.map((cfg, i) => (
          <div
            key={cfg.key}
            className="
              relative overflow-hidden rounded-2xl p-5
              bg-white border border-slate-200 shadow-md
              dark:bg-white/5 dark:border-white/10 dark:shadow-none
              hover:shadow-lg hover:-translate-y-0.5
              transition-all duration-300
            "
          >
            {/* Accent gradient strip at top */}
            <div className={`absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r ${cfg.accent}`} />

            <div className="flex items-center justify-between mb-3">
              <div className={`p-2.5 rounded-xl ${cfg.iconBg}`}>
                <cfg.icon className={`w-5 h-5 ${cfg.iconColor}`} />
              </div>
              <TrendingUp className="w-4 h-4 text-emerald-500 opacity-70" />
            </div>

            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {cfg.name}
            </p>

            {loading ? (
              <div className="h-8 w-24 mt-1 rounded-lg bg-muted/60 animate-pulse" />
            ) : (
              <p className="text-2xl font-bold mt-1 text-foreground">
                {statValues[i]}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* ── Secondary stats (total users + departments) ── */}
      {stats && (
        <div className="flex flex-wrap gap-3">
          <div className="
            flex items-center gap-3 px-4 py-3 rounded-2xl
            bg-white border border-slate-200 shadow-sm
            dark:bg-white/5 dark:border-white/10
          ">
            <div className="p-2 rounded-lg bg-violet-500/10">
              <Users className="w-4 h-4 text-violet-500" />
            </div>
            <div>
              <p className="text-[11px] text-muted-foreground uppercase tracking-wide">
                {isRoot() ? "Total Users" : "Dept Users"}
              </p>
              <p className="font-bold text-lg leading-none">{stats.total_users}</p>
            </div>
          </div>

          {isRoot() && (
            <div className="
              flex items-center gap-3 px-4 py-3 rounded-2xl
              bg-white border border-slate-200 shadow-sm
              dark:bg-white/5 dark:border-white/10
            ">
              <div className="p-2 rounded-lg bg-cyan-500/10">
                <Building2 className="w-4 h-4 text-cyan-500" />
              </div>
              <div>
                <p className="text-[11px] text-muted-foreground uppercase tracking-wide">Departments</p>
                <p className="font-bold text-lg leading-none">{stats.departments}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Main content grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Recent Queries */}
        <div className="
          lg:col-span-2 rounded-2xl overflow-hidden
          bg-white border border-slate-200 shadow-md
          dark:bg-white/5 dark:border-white/10 dark:shadow-none
        ">
          <div className="px-6 py-4 border-b border-black/5 dark:border-white/10 flex items-center justify-between">
            <h2 className="font-semibold text-sm">Recent Queries</h2>
            <span className="text-xs text-muted-foreground px-2 py-0.5 rounded-full bg-muted/60">
              Live
            </span>
          </div>

          {loading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-14 rounded-xl bg-muted/40 animate-pulse" />
              ))}
            </div>
          ) : visibleQueries.length === 0 ? (
            <div className="p-10 text-center text-muted-foreground text-sm">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-30" />
              No queries yet
            </div>
          ) : (
            <div className="divide-y divide-black/5 dark:divide-white/5">
              {visibleQueries.map((q) => (
                <div key={q.id}
                  className="px-6 py-3.5 hover:bg-black/[0.02] dark:hover:bg-white/[0.03] transition-colors group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                        {q.query_text}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                        <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium capitalize ${DEPT_BADGE[q.department] ?? DEPT_BADGE.general}`}>
                          {q.department}
                        </span>
                        <span className="text-[11px] text-muted-foreground">{q.username}</span>
                        <span className="text-[11px] text-muted-foreground">{timeAgo(q.timestamp)}</span>
                      </div>
                    </div>
                    <span className="text-[11px] text-muted-foreground whitespace-nowrap tabular-nums mt-0.5">
                      {formatResponseTime(q.response_time_ms)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="px-6 py-3 border-t border-black/5 dark:border-white/10">
            <button
              onClick={() => router.push("/dashboard/analytics")}
              className="text-sm text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
            >
              View all queries
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="
          rounded-2xl overflow-hidden
          bg-white border border-slate-200 shadow-md
          dark:bg-white/5 dark:border-white/10 dark:shadow-none
        ">
          <div className="px-6 py-4 border-b border-black/5 dark:border-white/10">
            <h2 className="font-semibold text-sm">Quick Actions</h2>
          </div>
          <div className="p-4 space-y-3">
            {/* Ask a Question */}
            <button
              onClick={() => router.push("/dashboard/query")}
              className="
                w-full p-4 rounded-xl text-left group transition-all duration-200
                bg-violet-50 border border-violet-200
                hover:bg-violet-100 hover:border-violet-300 hover:shadow-sm
                dark:bg-violet-500/10 dark:border-violet-500/20
                dark:hover:bg-violet-500/20
              "
            >
              <div className="flex items-center gap-2 mb-1.5">
                <div className="p-1.5 rounded-lg bg-violet-100 dark:bg-violet-500/20">
                  <MessageSquare className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                </div>
                <p className="font-semibold text-sm">Ask a Question</p>
              </div>
              <p className="text-xs text-muted-foreground">
                Get instant answers from your knowledge base
              </p>
            </button>

            {/* Upload Document */}
            <button
              onClick={() => router.push("/dashboard/ingest")}
              className="
                w-full p-4 rounded-xl text-left group transition-all duration-200
                bg-cyan-50 border border-cyan-200
                hover:bg-cyan-100 hover:border-cyan-300 hover:shadow-sm
                dark:bg-cyan-500/10 dark:border-cyan-500/20
                dark:hover:bg-cyan-500/20
              "
            >
              <div className="flex items-center gap-2 mb-1.5">
                <div className="p-1.5 rounded-lg bg-cyan-100 dark:bg-cyan-500/20">
                  <FileText className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                </div>
                <p className="font-semibold text-sm">Upload Document</p>
              </div>
              <p className="text-xs text-muted-foreground">
                Add new documents to your department
              </p>
            </button>

            {/* Agent Assistant */}
            <button
              onClick={() => router.push("/dashboard/agent")}
              className="
                w-full p-4 rounded-xl text-left group transition-all duration-200
                bg-emerald-50 border border-emerald-200
                hover:bg-emerald-100 hover:border-emerald-300 hover:shadow-sm
                dark:bg-emerald-500/10 dark:border-emerald-500/20
                dark:hover:bg-emerald-500/20
              "
            >
              <div className="flex items-center gap-2 mb-1.5">
                <div className="p-1.5 rounded-lg bg-emerald-100 dark:bg-emerald-500/20">
                  <Zap className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                </div>
                <p className="font-semibold text-sm">Agent Assistant</p>
              </div>
              <p className="text-xs text-muted-foreground">
                Run multi-step AI research tasks
              </p>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
