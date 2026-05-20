"use client";

import { useEffect, useState, useCallback } from "react";
import {
  FileText,
  MessageSquare,
  TrendingUp,
  Users,
  Clock,
  ArrowUpRight,
  Building2,
  RefreshCw,
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

export default function DashboardPage() {
  const { user } = useAuth();
  const firstName = user?.full_name?.split(" ")[0] || "User";

  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [queries, setQueries] = useState<RecentQuery[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsData, queriesData] = await Promise.all([
        api.getStats(),
        api.getRecentQueries(8),
      ]);
      setStats(statsData);
      setQueries(queriesData.queries ?? []);
      setLastRefreshed(new Date());
    } catch {
      // silently keep stale data on refresh failure
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [fetchData]);

  const statCards = stats
    ? [
        {
          name: "Total Documents",
          value: stats.total_documents.toLocaleString(),
          icon: FileText,
          color: "text-blue-500",
          bg: "bg-blue-500/10",
        },
        {
          name: "Queries Today",
          value: stats.queries_today.toLocaleString(),
          icon: MessageSquare,
          color: "text-green-500",
          bg: "bg-green-500/10",
        },
        {
          name: "Active Users",
          value: stats.active_users.toLocaleString(),
          icon: Users,
          color: "text-purple-500",
          bg: "bg-purple-500/10",
        },
        {
          name: "Avg Response",
          value: formatResponseTime(stats.avg_response_time),
          icon: Clock,
          color: "text-orange-500",
          bg: "bg-orange-500/10",
        },
      ]
    : [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Welcome back, {firstName}! Here&apos;s your Huron Knowledge Assistant overview.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
          {lastRefreshed && (
            <span>Updated {timeAgo(lastRefreshed.toISOString())}</span>
          )}
          <button
            onClick={fetchData}
            className="p-1.5 rounded hover:bg-accent transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="p-6 rounded-xl border border-border bg-card animate-pulse h-32"
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {statCards.map((stat) => (
            <div
              key={stat.name}
              className="p-6 rounded-xl border border-border bg-card hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`p-2 rounded-lg ${stat.bg}`}>
                  <stat.icon className={`w-5 h-5 ${stat.color}`} />
                </div>
                <TrendingUp className="w-4 h-4 text-green-500" />
              </div>
              <h3 className="text-muted-foreground text-sm">{stat.name}</h3>
              <p className="text-2xl font-bold mt-1">{stat.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Additional stats row (total users / departments) */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 max-w-sm">
          <div className="p-4 rounded-xl border border-border bg-card flex items-center gap-3">
            <Users className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Total Users</p>
              <p className="font-semibold">{stats.total_users}</p>
            </div>
          </div>
          <div className="p-4 rounded-xl border border-border bg-card flex items-center gap-3">
            <Building2 className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Departments</p>
              <p className="font-semibold">{stats.departments}</p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Queries */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-card">
          <div className="p-6 border-b border-border">
            <h2 className="font-semibold">Recent Queries</h2>
          </div>
          {loading ? (
            <div className="p-6 space-y-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-12 rounded bg-accent/30 animate-pulse" />
              ))}
            </div>
          ) : queries.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">No queries yet.</p>
          ) : (
            <div className="divide-y divide-border">
              {queries.map((q) => (
                <div key={q.id} className="p-4 hover:bg-accent/50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0 pr-4">
                      <p className="font-medium text-sm truncate">{q.query_text}</p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary capitalize">
                          {q.department}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {q.username}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {timeAgo(q.timestamp)}
                        </span>
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatResponseTime(q.response_time_ms)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="p-4 border-t border-border">
            <button className="text-sm text-primary hover:underline flex items-center">
              View all queries
              <ArrowUpRight className="w-4 h-4 ml-1" />
            </button>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="rounded-xl border border-border bg-card">
          <div className="p-6 border-b border-border">
            <h2 className="font-semibold">Quick Actions</h2>
          </div>
          <div className="p-4 space-y-3">
            <button className="w-full p-4 rounded-lg border border-border hover:bg-accent transition-colors text-left">
              <MessageSquare className="w-5 h-5 text-primary mb-2" />
              <p className="font-medium text-sm">Ask a Question</p>
              <p className="text-xs text-muted-foreground mt-1">
                Get instant answers from your knowledge base
              </p>
            </button>
            <button className="w-full p-4 rounded-lg border border-border hover:bg-accent transition-colors text-left">
              <FileText className="w-5 h-5 text-primary mb-2" />
              <p className="font-medium text-sm">Upload Document</p>
              <p className="text-xs text-muted-foreground mt-1">
                Add new documents to your department
              </p>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
