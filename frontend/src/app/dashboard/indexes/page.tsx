"use client";

import { Database, Plus, Trash2, RefreshCw, HardDrive, FileText, AlertCircle } from "lucide-react";
import { useState, useEffect } from "react";

interface IndexInfo {
  name: string;
  type: string;
  documents: number;
  size_mb: number;
  status: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function IndexManagementPage() {
  const [indexes, setIndexes] = useState<IndexInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIndexes = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/indexes`);
      if (!response.ok) {
        throw new Error("Failed to fetch indexes");
      }
      const data = await response.json();
      setIndexes(data.indexes || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load indexes");
      console.error("Error fetching indexes:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIndexes();
  }, []);

  const totalDocuments = indexes.reduce((acc, i) => acc + i.documents, 0);
  const totalSizeMB = indexes.reduce((acc, i) => acc + i.size_mb, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Database className="h-8 w-8 text-cyan-500" />
            Index Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage vector indexes and document collections
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90">
          <Plus className="h-4 w-4" />
          Create Index
        </button>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl border border-red-500/50 bg-red-500/10 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span className="text-red-500">{error}</span>
          <button onClick={fetchIndexes} className="ml-auto text-sm underline">Retry</button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <Database className="h-8 w-8 text-cyan-500" />
            <div>
              <p className="text-2xl font-bold">{loading ? "..." : indexes.length}</p>
              <p className="text-sm text-muted-foreground">Total Indexes</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <FileText className="h-8 w-8 text-blue-500" />
            <div>
              <p className="text-2xl font-bold">{loading ? "..." : totalDocuments.toLocaleString()}</p>
              <p className="text-sm text-muted-foreground">Total Documents</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <HardDrive className="h-8 w-8 text-green-500" />
            <div>
              <p className="text-2xl font-bold">{loading ? "..." : `${totalSizeMB.toFixed(1)} MB`}</p>
              <p className="text-sm text-muted-foreground">Local Storage</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <RefreshCw className={`h-8 w-8 text-orange-500 ${loading ? 'animate-spin' : ''}`} />
            <div>
              <p className="text-2xl font-bold">{indexes.filter(i => i.status === 'syncing').length}</p>
              <p className="text-sm text-muted-foreground">Syncing</p>
            </div>
          </div>
        </div>
      </div>

      {/* Index Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-4 font-medium">Index Name</th>
              <th className="text-left p-4 font-medium">Type</th>
              <th className="text-left p-4 font-medium">Documents</th>
              <th className="text-left p-4 font-medium">Size</th>
              <th className="text-left p-4 font-medium">Status</th>
              <th className="text-left p-4 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-muted-foreground">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                  Loading indexes...
                </td>
              </tr>
            ) : indexes.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-muted-foreground">
                  No indexes found. Create one to get started.
                </td>
              </tr>
            ) : (
              indexes.map((index) => (
                <tr key={index.name} className="border-t border-border hover:bg-muted/30">
                  <td className="p-4 font-medium">{index.name}</td>
                  <td className="p-4">
                    <span className={`px-2 py-1 rounded text-xs ${
                      index.type === 'FAISS' ? 'bg-blue-500/10 text-blue-500' :
                      index.type === 'Pinecone' ? 'bg-purple-500/10 text-purple-500' :
                      'bg-green-500/10 text-green-500'
                    }`}>
                      {index.type}
                    </span>
                  </td>
                  <td className="p-4">{index.documents.toLocaleString()}</td>
                  <td className="p-4">{index.size_mb.toFixed(2)} MB</td>
                  <td className="p-4">
                    <span className={`flex items-center gap-1 ${
                      index.status === 'active' ? 'text-green-500' : 'text-yellow-500'
                    }`}>
                      <span className={`w-2 h-2 rounded-full ${
                        index.status === 'active' ? 'bg-green-500' : 'bg-yellow-500 animate-pulse'
                      }`}></span>
                      {index.status}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <button className="p-2 hover:bg-accent rounded-lg" title="Refresh" onClick={fetchIndexes}>
                        <RefreshCw className="h-4 w-4" />
                      </button>
                      <button className="p-2 hover:bg-red-500/10 text-red-500 rounded-lg" title="Delete">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
