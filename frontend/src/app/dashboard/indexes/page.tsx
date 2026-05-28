"use client";

import { Database, RefreshCw, HardDrive, FileText, AlertCircle, Shield } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { api } from "../../../services/api";

interface IndexRow {
  name:           string;
  dept:           string;
  display_name:   string;
  type:           string;
  documents:      number;
  classification: string;
  status:         string;
}

export default function IndexManagementPage() {
  const [indexes, setIndexes] = useState<IndexRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const fetchIndexes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getIndexes();
      // Backend returns { indexes: [{name, dept, display_name, type, documents, classification, status}] }
      setIndexes((data.indexes as unknown as IndexRow[]) ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load indexes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchIndexes(); }, [fetchIndexes]);

  const totalDocuments = indexes.reduce((acc, i) => acc + (i.documents ?? 0), 0);

  const classColor: Record<string, string> = {
    public:       "bg-green-500/10 text-green-600 dark:text-green-400",
    internal:     "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    confidential: "bg-orange-500/10 text-orange-600 dark:text-orange-400",
    restricted:   "bg-red-500/10 text-red-600 dark:text-red-400",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Database className="h-8 w-8 text-cyan-500" />
            Index Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Pinecone namespace indexes — one per department
          </p>
        </div>
        <button
          onClick={fetchIndexes}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-red-500/50 bg-red-500/10 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 shrink-0" />
          <span className="text-red-500">{error}</span>
          <button onClick={fetchIndexes} className="ml-auto text-sm underline">Retry</button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-border bg-card flex items-center gap-3">
          <Database className="h-8 w-8 text-cyan-500 shrink-0" />
          <div>
            <p className="text-2xl font-bold">{loading ? "…" : indexes.length}</p>
            <p className="text-sm text-muted-foreground">Namespaces</p>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card flex items-center gap-3">
          <FileText className="h-8 w-8 text-blue-500 shrink-0" />
          <div>
            <p className="text-2xl font-bold">{loading ? "…" : totalDocuments.toLocaleString()}</p>
            <p className="text-sm text-muted-foreground">Total Documents</p>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card flex items-center gap-3">
          <HardDrive className="h-8 w-8 text-green-500 shrink-0" />
          <div>
            <p className="text-2xl font-bold">Pinecone</p>
            <p className="text-sm text-muted-foreground">Vector Store</p>
          </div>
        </div>
      </div>

      {/* Index Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-4 font-medium">Department</th>
              <th className="text-left p-4 font-medium">Namespace</th>
              <th className="text-left p-4 font-medium">Classification</th>
              <th className="text-left p-4 font-medium">Documents</th>
              <th className="text-left p-4 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-muted-foreground">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                  Loading indexes…
                </td>
              </tr>
            ) : indexes.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-muted-foreground">
                  No indexes found. Ingest documents to create a namespace.
                </td>
              </tr>
            ) : (
              indexes.map((idx) => (
                <tr key={idx.name} className="border-t border-border hover:bg-muted/30">
                  <td className="p-4">
                    <p className="font-medium">{idx.display_name}</p>
                    <p className="text-xs text-muted-foreground uppercase">{idx.dept}</p>
                  </td>
                  <td className="p-4 font-mono text-xs text-muted-foreground">{idx.name}</td>
                  <td className="p-4">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${classColor[idx.classification] ?? classColor.internal}`}>
                      <Shield className="h-3 w-3" />
                      {idx.classification}
                    </span>
                  </td>
                  <td className="p-4">{(idx.documents ?? 0).toLocaleString()}</td>
                  <td className="p-4">
                    <span className="flex items-center gap-1.5 text-green-500 text-sm">
                      <span className="w-2 h-2 rounded-full bg-green-500" />
                      active
                    </span>
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
