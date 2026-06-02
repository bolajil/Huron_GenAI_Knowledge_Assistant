"use client";

import { useEffect, useState } from "react";
import { HardDrive, Cloud, Database, Trash2, Loader2, CheckCircle, XCircle } from "lucide-react";

interface HealthData {
  status: string;
  db: { status: string; backend: string };
  redis: { status: string };
  pinecone: { status: string };
  version: string;
}

export default function StoragePage() {
  const [health, setHealth]   = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch((err) => setError(err.message || "Failed to reach backend"))
      .finally(() => setLoading(false));
  }, []);

  const StatusIcon = ({ ok }: { ok: boolean }) =>
    ok ? <CheckCircle className="h-5 w-5 text-green-500" /> : <XCircle className="h-5 w-5 text-red-500" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <HardDrive className="h-8 w-8 text-cyan-500" />
          Storage Settings
        </h1>
        <p className="text-muted-foreground mt-1">
          Storage backends and data retention configuration
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

      {!loading && !error && health && (
        <>
          {/* Backend Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl border border-border bg-card">
              <div className="flex items-center justify-between mb-2">
                <Database className="h-8 w-8 text-blue-500" />
                <StatusIcon ok={health.db?.status === "ok"} />
              </div>
              <p className="text-lg font-bold capitalize">{health.db?.backend ?? "—"}</p>
              <p className="text-sm text-muted-foreground">Primary Database</p>
              <p className={`text-xs mt-1 font-medium ${health.db?.status === "ok" ? "text-green-500" : "text-red-500"}`}>
                {health.db?.status === "ok" ? "Connected" : "Disconnected"}
              </p>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card">
              <div className="flex items-center justify-between mb-2">
                <Cloud className="h-8 w-8 text-purple-500" />
                <StatusIcon ok={health.pinecone?.status === "ok"} />
              </div>
              <p className="text-lg font-bold">Pinecone</p>
              <p className="text-sm text-muted-foreground">Vector Store</p>
              <p className={`text-xs mt-1 font-medium ${health.pinecone?.status === "ok" ? "text-green-500" : health.pinecone?.status === "disabled" ? "text-yellow-500" : "text-red-500"}`}>
                {health.pinecone?.status === "ok" ? "Connected" : health.pinecone?.status === "disabled" ? "No API Key" : "Error"}
              </p>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card">
              <div className="flex items-center justify-between mb-2">
                <HardDrive className="h-8 w-8 text-green-500" />
                <StatusIcon ok={health.redis?.status === "ok"} />
              </div>
              <p className="text-lg font-bold">Redis</p>
              <p className="text-sm text-muted-foreground">Cache / Sessions</p>
              <p className={`text-xs mt-1 font-medium ${health.redis?.status === "ok" ? "text-green-500" : health.redis?.status === "disabled" ? "text-yellow-500" : "text-red-500"}`}>
                {health.redis?.status === "ok" ? "Connected" : health.redis?.status === "disabled" ? "Disabled" : "Error"}
              </p>
            </div>
          </div>

          {/* System Version */}
          <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-3">
            <div className={`h-3 w-3 rounded-full ${health.status === "healthy" ? "bg-green-500" : "bg-yellow-500"}`} />
            <span className="text-sm font-medium">
              System {health.status} — API version {health.version}
            </span>
          </div>
        </>
      )}

      {/* Data Retention Policy */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="font-semibold mb-4">Data Retention Policy</h2>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-muted-foreground">Query Logs Retention</label>
            <select className="w-full mt-1 p-2 rounded-lg bg-background border border-border">
              <option>30 days</option>
              <option>90 days</option>
              <option>1 year</option>
              <option>Forever</option>
            </select>
          </div>
          <div>
            <label className="text-sm text-muted-foreground">External Document TTL</label>
            <select className="w-full mt-1 p-2 rounded-lg bg-background border border-border">
              <option>90 days</option>
              <option>180 days</option>
              <option>1 year</option>
            </select>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors">
            <Trash2 className="h-4 w-4" />
            Clear Cache
          </button>
        </div>
      </div>
    </div>
  );
}
