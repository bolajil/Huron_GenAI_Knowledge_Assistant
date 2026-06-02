"use client";

import { useEffect, useState } from "react";
import { ThumbsUp, MessageSquare, Star, BarChart3, Loader2, TrendingUp } from "lucide-react";
import { api } from "../../../services/api";
import type { RecentQuery, StatsResponse as Stats } from "../../../services/api";

export default function FeedbackAnalyticsPage() {
  const [queries, setQueries]   = useState<RecentQuery[]>([]);
  const [stats, setStats]       = useState<Stats | null>(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState("");

  useEffect(() => {
    Promise.all([
      api.getStats(),
      api.getRecentQueries(20),
    ])
      .then(([statsData, queriesData]) => {
        setStats(statsData);
        setQueries(queriesData.queries || []);
      })
      .catch((err) => setError(err.message || "Failed to load data"))
      .finally(() => setLoading(false));
  }, []);

  const deptCounts = queries.reduce<Record<string, number>>((acc, q) => {
    acc[q.department] = (acc[q.department] || 0) + 1;
    return acc;
  }, {});

  const totalQueries = queries.length;

  const timeAgo = (iso: string) => {
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (diff < 60)  return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <ThumbsUp className="h-8 w-8 text-green-500" />
          Feedback Analytics
        </h1>
        <p className="text-muted-foreground mt-1">
          Query activity and system usage metrics
        </p>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
          {error}
        </div>
      )}

      {!loading && !error && stats && (
        <>
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-border bg-card">
              <div className="flex items-center gap-3">
                <MessageSquare className="h-8 w-8 text-blue-500" />
                <div>
                  <p className="text-2xl font-bold">{stats.queries_today.toLocaleString()}</p>
                  <p className="text-sm text-muted-foreground">Queries Today</p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-xl border border-border bg-card">
              <div className="flex items-center gap-3">
                <Star className="h-8 w-8 text-yellow-500" />
                <div>
                  <p className="text-2xl font-bold">
                    {stats.avg_response_time > 0 ? `${stats.avg_response_time}s` : "—"}
                  </p>
                  <p className="text-sm text-muted-foreground">Avg Response Time</p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-xl border border-border bg-card">
              <div className="flex items-center gap-3">
                <TrendingUp className="h-8 w-8 text-purple-500" />
                <div>
                  <p className="text-2xl font-bold">{stats.active_users}</p>
                  <p className="text-sm text-muted-foreground">Active Users</p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-xl border border-border bg-card">
              <div className="flex items-center gap-3">
                <BarChart3 className="h-8 w-8 text-green-500" />
                <div>
                  <p className="text-2xl font-bold">{totalQueries}</p>
                  <p className="text-sm text-muted-foreground">Recent Queries</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Queries by Department */}
            <div className="rounded-xl border border-border bg-card p-6">
              <h2 className="font-semibold mb-4 flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Queries by Department
              </h2>
              {Object.keys(deptCounts).length === 0 ? (
                <p className="text-sm text-muted-foreground">No query data yet</p>
              ) : (
                <div className="space-y-4">
                  {Object.entries(deptCounts)
                    .sort((a, b) => b[1] - a[1])
                    .map(([dept, count]) => {
                      const pct = totalQueries > 0 ? Math.round((count / totalQueries) * 100) : 0;
                      return (
                        <div key={dept}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium capitalize">{dept}</span>
                            <span className="text-sm text-muted-foreground">{count} queries ({pct}%)</span>
                          </div>
                          <div className="w-full h-2 bg-muted rounded-full">
                            <div className="h-full bg-primary rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}
            </div>

            {/* Recent Queries */}
            <div className="rounded-xl border border-border bg-card p-6">
              <h2 className="font-semibold mb-4">Recent Queries</h2>
              {queries.length === 0 ? (
                <p className="text-sm text-muted-foreground">No queries yet</p>
              ) : (
                <div className="space-y-3">
                  {queries.slice(0, 8).map((q) => (
                    <div key={q.id} className="p-3 rounded-lg bg-muted/50">
                      <p className="text-sm font-medium truncate">{q.query_text}</p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-xs px-2 py-0.5 rounded bg-primary/10 text-primary capitalize">
                          {q.department}
                        </span>
                        {q.response_time_ms > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {q.response_time_ms}ms
                          </span>
                        )}
                        <span className="text-xs text-muted-foreground ml-auto">
                          {timeAgo(q.timestamp)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
