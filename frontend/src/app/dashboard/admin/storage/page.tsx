"use client";

import { HardDrive, Cloud, Database, Trash2 } from "lucide-react";

export default function StoragePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <HardDrive className="h-8 w-8 text-cyan-500" />
          Storage Settings
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage storage backends and data retention
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-border bg-card">
          <Database className="h-8 w-8 text-blue-500 mb-2" />
          <p className="text-2xl font-bold">135 MB</p>
          <p className="text-sm text-muted-foreground">Local FAISS Storage</p>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <Cloud className="h-8 w-8 text-purple-500 mb-2" />
          <p className="text-2xl font-bold">2.4 GB</p>
          <p className="text-sm text-muted-foreground">Cloud (Pinecone)</p>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <HardDrive className="h-8 w-8 text-green-500 mb-2" />
          <p className="text-2xl font-bold">890 MB</p>
          <p className="text-sm text-muted-foreground">Backup Storage</p>
        </div>
      </div>

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
          <button className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600">
            <Trash2 className="h-4 w-4" />
            Clear Cache
          </button>
        </div>
      </div>
    </div>
  );
}
