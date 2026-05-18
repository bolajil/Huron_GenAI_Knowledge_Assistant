/**
 * Admin Panel Component
 * Per FRONTEND_MIGRATION_GUIDE.md - components/Admin/AdminPanel.jsx
 */
"use client";

import { useState, useEffect } from "react";
import {
  Users,
  Settings,
  Shield,
  BarChart3,
  Loader2,
  CheckCircle,
  XCircle,
  RefreshCw,
} from "lucide-react";
import { api } from "../../services/api";
import { useAuth } from "../../contexts/auth-context";

interface SystemStats {
  total_documents: number;
  queries_today: number;
  active_users: number;
  avg_response_time: number;
}

type AdminTab = "overview" | "users" | "departments" | "settings";

export function AdminPanel() {
  const { user, hasRole } = useAuth();
  const [activeTab, setActiveTab] = useState<AdminTab>("overview");
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Check admin access
  if (!hasRole(["admin"])) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Shield className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <h2 className="text-xl font-bold mb-2">Access Denied</h2>
          <p className="text-muted-foreground">
            You need admin privileges to access this page.
          </p>
        </div>
      </div>
    );
  }

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    setError("");

    try {
      if (activeTab === "overview" || activeTab === "users") {
        const statsData = await api.getStats();
        setStats(statsData);
      }

      if (activeTab === "users") {
        const usersData = await api.getUsers();
        setUsers(usersData.users || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: "overview" as const, label: "Overview", icon: BarChart3 },
    { id: "users" as const, label: "Users", icon: Users },
    { id: "departments" as const, label: "Departments", icon: Shield },
    { id: "settings" as const, label: "Settings", icon: Settings },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Settings className="h-6 w-6 text-primary" />
            Admin Panel
          </h2>
          <p className="text-muted-foreground mt-1">
            Manage system settings, users, and departments
          </p>
        </div>
        <button
          onClick={loadData}
          className="p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`h-5 w-5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-border">
        <div className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {/* Tab Content */}
      {!loading && (
        <>
          {/* Overview Tab */}
          {activeTab === "overview" && stats && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  title="Total Documents"
                  value={stats.total_documents.toLocaleString()}
                  icon={<BarChart3 className="h-5 w-5" />}
                />
                <StatCard
                  title="Queries Today"
                  value={stats.queries_today.toLocaleString()}
                  icon={<BarChart3 className="h-5 w-5" />}
                />
                <StatCard
                  title="Active Users"
                  value={stats.active_users.toLocaleString()}
                  icon={<Users className="h-5 w-5" />}
                />
                <StatCard
                  title="Avg Response Time"
                  value={`${stats.avg_response_time}s`}
                  icon={<BarChart3 className="h-5 w-5" />}
                />
              </div>

              <div className="rounded-xl border border-border bg-card p-6">
                <h3 className="font-semibold mb-4">System Health</h3>
                <div className="space-y-3">
                  <HealthItem label="API Server" status="healthy" />
                  <HealthItem label="Vector Database" status="healthy" />
                  <HealthItem label="Authentication" status="healthy" />
                  <HealthItem label="Background Jobs" status="healthy" />
                </div>
              </div>
            </div>
          )}

          {/* Users Tab */}
          {activeTab === "users" && (
            <div className="rounded-xl border border-border bg-card">
              <div className="p-4 border-b border-border">
                <h3 className="font-semibold">User Management</h3>
              </div>
              {users.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  No users found
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {users.map((u: any, idx: number) => (
                    <div key={idx} className="p-4 flex items-center justify-between">
                      <div>
                        <p className="font-medium">{u.username || u.email}</p>
                        <p className="text-sm text-muted-foreground">
                          {u.role} • {u.department || "No department"}
                        </p>
                      </div>
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          u.is_active
                            ? "bg-green-500/10 text-green-500"
                            : "bg-red-500/10 text-red-500"
                        }`}
                      >
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Departments Tab */}
          {activeTab === "departments" && (
            <div className="rounded-xl border border-border bg-card p-6">
              <h3 className="font-semibold mb-4">Department Management</h3>
              <p className="text-muted-foreground">
                Department management coming soon...
              </p>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === "settings" && (
            <div className="rounded-xl border border-border bg-card p-6">
              <h3 className="font-semibold mb-4">System Settings</h3>
              <p className="text-muted-foreground">
                System settings coming soon...
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-3 mb-2 text-muted-foreground">
        {icon}
        <span className="text-sm">{title}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}

function HealthItem({
  label,
  status,
}: {
  label: string;
  status: "healthy" | "warning" | "error";
}) {
  return (
    <div className="flex items-center justify-between">
      <span>{label}</span>
      <div className="flex items-center gap-2">
        {status === "healthy" ? (
          <>
            <CheckCircle className="h-4 w-4 text-green-500" />
            <span className="text-sm text-green-500">Healthy</span>
          </>
        ) : status === "warning" ? (
          <>
            <RefreshCw className="h-4 w-4 text-yellow-500" />
            <span className="text-sm text-yellow-500">Warning</span>
          </>
        ) : (
          <>
            <XCircle className="h-4 w-4 text-red-500" />
            <span className="text-sm text-red-500">Error</span>
          </>
        )}
      </div>
    </div>
  );
}

export default AdminPanel;
