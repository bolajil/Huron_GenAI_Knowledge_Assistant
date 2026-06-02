"use client";

import { useEffect, useState } from "react";
import { Building2, Plus, Settings, Users, Loader2 } from "lucide-react";
import { api } from "../../../../services/api";
import type { Department } from "../../../../services/api";

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getDepartments()
      .then((res) => setDepartments(res.departments || []))
      .catch((err) => setError(err.message || "Failed to load departments"))
      .finally(() => setLoading(false));
  }, []);

  const classificationColor: Record<string, string> = {
    hipaa_phi:    "text-red-500 bg-red-500/10",
    restricted:   "text-orange-500 bg-orange-500/10",
    confidential: "text-yellow-500 bg-yellow-500/10",
    internal:     "text-blue-500 bg-blue-500/10",
    public:       "text-green-500 bg-green-500/10",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Building2 className="h-8 w-8 text-indigo-500" />
            Department Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage department namespaces and access
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">
          <Plus className="h-4 w-4" />
          Add Department
        </button>
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

      {!loading && !error && (
        <>
          <p className="text-sm text-muted-foreground">
            {departments.length} department{departments.length !== 1 ? "s" : ""} configured
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {departments.map((dept) => (
              <div
                key={dept.code}
                className="rounded-xl border border-border bg-card p-6 hover:border-primary/50 transition-colors"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold">{dept.display_name}</h3>
                  <button className="p-2 hover:bg-accent rounded-lg transition-colors">
                    <Settings className="h-4 w-4" />
                  </button>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Namespace</span>
                    <code className="px-2 py-0.5 rounded bg-muted text-xs">{dept.namespace.split("-").pop()}</code>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground flex items-center gap-1">
                      <Users className="h-3 w-3" /> Users
                    </span>
                    <span>{dept.user_count ?? "—"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Queries</span>
                    <span>{(dept.query_count ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Classification</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${classificationColor[dept.classification ?? ""] ?? "text-muted-foreground bg-muted"}`}>
                      {(dept.classification ?? "unknown").replace("_", " ")}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
