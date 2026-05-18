"use client";

import { Building2, Plus, Settings, Users } from "lucide-react";

const departments = [
  { name: "Human Resources", code: "hr", users: 45, documents: 1234, namespace: "hr" },
  { name: "Legal", code: "legal", users: 23, documents: 567, namespace: "legal" },
  { name: "Finance", code: "finance", users: 34, documents: 890, namespace: "finance" },
  { name: "Clinical", code: "clinical", users: 67, documents: 2341, namespace: "clinical" },
  { name: "Operations", code: "operations", users: 89, documents: 456, namespace: "operations" },
  { name: "IT", code: "it", users: 28, documents: 345, namespace: "it" },
];

export default function DepartmentsPage() {
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
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg">
          <Plus className="h-4 w-4" />
          Add Department
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {departments.map((dept) => (
          <div key={dept.code} className="rounded-xl border border-border bg-card p-6 hover:border-primary/50 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">{dept.name}</h3>
              <button className="p-2 hover:bg-accent rounded-lg">
                <Settings className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Namespace</span>
                <code className="px-2 py-0.5 rounded bg-muted text-xs">{dept.namespace}</code>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-1">
                  <Users className="h-3 w-3" /> Users
                </span>
                <span>{dept.users}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Documents</span>
                <span>{dept.documents.toLocaleString()}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
