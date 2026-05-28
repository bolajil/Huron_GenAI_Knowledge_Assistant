"use client";

import { useEffect, useState, useCallback } from "react";
import {
  BarChart3, TrendingUp, Users, FileText, Clock,
  RefreshCw, AlertCircle, PackagePlus, ArrowUpCircle, CheckCircle2,
} from "lucide-react";
import { api } from "../../../services/api";
import type { StatsResponse, RecentQuery, DocumentVersionEvent } from "../../../services/api";

const DEPT_COLORS: Record<string, string> = {
  hr:         "bg-blue-500",
  legal:      "bg-purple-500",
  finance:    "bg-green-500",
  clinical:   "bg-orange-500",
  operations: "bg-cyan-500",
  it:         "bg-pink-500",
  marketing:  "bg-yellow-500",
  external:   "bg-gray-500",
  general:    "bg-indigo-500",
};

function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
}

function timeAgo(ts: string): string {
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// Group recent queries into last-7-days buckets for the bar chart
function buildDailyBuckets(queries: RecentQuery[]): { label: string; count: number }[] {
  const buckets: Record<string, number> = {};
  const now = new Date();
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const key = d.toLocaleDateString("en-US", { weekday: "short" });
    buckets[key] = 0;
  }
  queries.forEach((q) => {
    const d = new Date(q.timestamp);
    const key = d.toLocaleDateString("en-US", { weekday: "short" });
    if (key in buckets) buckets[key]++;
  });
  return Object.entries(buckets).map(([label, count]) => ({ label, count }));
}

// Aggregate queries by department
function buildDeptCounts(queries: RecentQuery[]): { dept: string; count: number }[] {
  const counts: Record<string, number> = {};
  queries.forEach((q) => {
    const d = q.department || "general";
    counts[d] = (counts[d] ?? 0) + 1;
  });
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([dept, count]) => ({ dept, count }));
}

export default function AnalyticsPage() {
  const [stats,    setStats]    = useState<StatsResponse | null>(null);
  const [queries,  setQueries]  = useState<RecentQuery[]>([]);
  const [docVersions, setDocVersions] = useState<DocumentVersionEvent[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, queryData, versionData] = await Promise.all([
        api.getStats(),
        api.getRecentQueries(50),
        api.getRecentDocumentVersions(30),
      ]);
      setStats(statsData);
      setDocVersions(versionData.versions ?? []);
      setQueries(queryData.queries ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const dailyBuckets = buildDailyBuckets(queries);
  const deptCounts   = buildDeptCounts(queries);
  const maxDay       = Math.max(...dailyBuckets.map((b) => b.count), 1);
  const maxDept      = Math.max(...deptCounts.map((d) => d.count), 1);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <BarChart3 className="h-8 w-8 text-blue-500" />
            Analytics
          </h1>
          <p className="text-muted-foreground mt-1">
            Live usage metrics from the query log
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-accent text-sm disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-red-500/50 bg-red-500/10 p-4">
          <AlertCircle className="h-5 w-5 text-red-500 shrink-0" />
          <p className="text-red-500 text-sm">{error}</p>
        </div>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Total Documents",
            value: loading ? "…" : (stats?.total_documents ?? 0).toLocaleString(),
            icon: FileText,
            color: "text-blue-500",
          },
          {
            label: "Queries Today",
            value: loading ? "…" : (stats?.queries_today ?? 0).toLocaleString(),
            icon: TrendingUp,
            color: "text-green-500",
          },
          {
            label: "Active Users",
            value: loading ? "…" : (stats?.active_users ?? 0).toLocaleString(),
            icon: Users,
            color: "text-purple-500",
          },
          {
            label: "Avg Response Time",
            value: loading ? "…" : formatMs(stats?.avg_response_time ?? 0),
            icon: Clock,
            color: "text-orange-500",
          },
        ].map((m, i) => (
          <div key={i} className="p-5 rounded-xl border border-border bg-card">
            <m.icon className={`h-5 w-5 ${m.color} mb-3`} />
            <p className="text-2xl font-bold">{m.value}</p>
            <p className="text-sm text-muted-foreground mt-0.5">{m.label}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Queries — last 7 days */}
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4">Queries — Last 7 Days</h2>
          {queries.length === 0 && !loading ? (
            <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
              No query data yet. Run some queries to see activity.
            </div>
          ) : (
            <div className="h-48 flex items-end justify-between gap-2">
              {dailyBuckets.map((b) => (
                <div key={b.label} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-xs text-muted-foreground">{b.count || ""}</span>
                  <div
                    className="w-full bg-primary/80 rounded-t hover:bg-primary transition-colors min-h-[4px]"
                    style={{ height: `${Math.max((b.count / maxDay) * 100, b.count > 0 ? 4 : 0)}%` }}
                    title={`${b.count} queries`}
                  />
                  <span className="text-xs text-muted-foreground">{b.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Queries by Department */}
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4">Queries by Department</h2>
          {deptCounts.length === 0 && !loading ? (
            <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
              No department data yet.
            </div>
          ) : (
            <div className="space-y-3">
              {deptCounts.slice(0, 6).map((d) => (
                <div key={d.dept}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium capitalize">{d.dept}</span>
                    <span className="text-sm text-muted-foreground">{d.count}</span>
                  </div>
                  <div className="w-full h-2 bg-muted rounded-full">
                    <div
                      className={`h-full rounded-full ${DEPT_COLORS[d.dept] ?? "bg-primary"}`}
                      style={{ width: `${(d.count / maxDept) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Document Version Feed */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold flex items-center gap-2">
            <PackagePlus className="h-5 w-5 text-blue-500" />
            Document Version Feed
          </h2>
          <span className="text-xs text-muted-foreground">Last {docVersions.length} ingestion events</span>
        </div>
        {loading ? (
          <div className="flex justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : docVersions.length === 0 ? (
          <p className="text-center text-sm text-muted-foreground py-8">
            No documents ingested yet. Upload a document to see version history here.
          </p>
        ) : (
          <div className="space-y-3">
            {docVersions.map((v, i) => (
              <div
                key={`${v.doc_id}-${v.version}-${i}`}
                className="flex items-start gap-3 p-3 rounded-lg border border-border hover:bg-muted/40 transition-colors"
              >
                <div className="mt-0.5 shrink-0">
                  {v.is_latest ? (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  ) : (
                    <ArrowUpCircle className="h-5 w-5 text-muted-foreground/50" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-medium truncate max-w-xs" title={v.source_file}>
                      {v.source_file}
                    </p>
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs text-white ${
                        DEPT_COLORS[v.dept] ?? "bg-primary"
                      }`}
                    >
                      {v.dept_name ?? v.dept}
                    </span>
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-mono bg-muted text-muted-foreground">
                      {v.version}
                    </span>
                    {v.version !== "v1" && v.is_latest && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-blue-500/15 text-blue-600 dark:text-blue-400 font-medium">
                        <ArrowUpCircle className="h-3 w-3" />
                        NEW VERSION
                      </span>
                    )}
                    {!v.is_latest && (
                      <span className="inline-block px-2 py-0.5 rounded text-xs bg-muted text-muted-foreground">
                        superseded
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {v.chunk_count} chunks · ingested by{" "}
                    <span className="font-medium">{v.ingested_by}</span> ·{" "}
                    {timeAgo(v.ingested_at)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Queries table */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">Recent Queries</h2>
          <span className="text-xs text-muted-foreground">Last {queries.length} queries</span>
        </div>
        {loading ? (
          <div className="flex justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : queries.length === 0 ? (
          <p className="text-center text-sm text-muted-foreground py-8">
            No queries recorded yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="py-3 pr-4 font-medium text-sm">Query</th>
                  <th className="py-3 pr-4 font-medium text-sm">User</th>
                  <th className="py-3 pr-4 font-medium text-sm">Department</th>
                  <th className="py-3 pr-4 font-medium text-sm">Response</th>
                  <th className="py-3 font-medium text-sm">When</th>
                </tr>
              </thead>
              <tbody>
                {queries.map((row) => (
                  <tr key={row.id} className="border-b border-border hover:bg-muted/40">
                    <td className="py-3 pr-4 max-w-xs">
                      <p className="text-sm truncate" title={row.query_text}>
                        {row.query_text}
                      </p>
                    </td>
                    <td className="py-3 pr-4 text-sm text-muted-foreground">{row.username}</td>
                    <td className="py-3 pr-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs text-white capitalize ${
                          DEPT_COLORS[row.department] ?? "bg-primary"
                        }`}
                      >
                        {row.department}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-sm text-muted-foreground">
                      {formatMs(row.response_time_ms)}
                    </td>
                    <td className="py-3 text-sm text-muted-foreground whitespace-nowrap">
                      {timeAgo(row.timestamp)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
