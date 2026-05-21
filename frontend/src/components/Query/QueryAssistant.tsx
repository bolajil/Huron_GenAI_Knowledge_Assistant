"use client";

import { useState } from "react";
import { Search, Loader2, FileText, AlertCircle, Lock } from "lucide-react";
import { api } from "../../services/api";
import { useAuth } from "../../contexts/auth-context";

interface QueryResult {
  status: string;
  query: string;
  results: string;
  sources: Array<{ title: string; page?: number }>;
}

const ALL_DEPARTMENTS = [
  { value: "hr",         label: "Human Resources" },
  { value: "legal",      label: "Legal" },
  { value: "finance",    label: "Finance" },
  { value: "clinical",   label: "Clinical" },
  { value: "operations", label: "Operations" },
  { value: "it",         label: "IT & Engineering" },
  { value: "marketing",  label: "Marketing" },
  { value: "external",   label: "External" },
];

export function QueryAssistant() {
  const { user, isRoot } = useAuth();

  const userDept = user?.department ?? "general";
  const [query, setQuery] = useState("");
  // Root can pick any dept; others are locked to their own
  const [selectedDept, setSelectedDept] = useState(isRoot() ? "hr" : userDept);
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<QueryResult | null>(null);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    if (!query.trim()) {
      setError("Please enter a question");
      return;
    }
    setLoading(true);
    setError("");
    setResults(null);
    try {
      const dept = isRoot() ? selectedDept : userDept;
      const response = await api.query(query, dept, topK);
      setResults(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Search className="h-6 w-6 text-primary" />
          Query Assistant
        </h2>
        <p className="text-muted-foreground mt-1">
          Search your{" "}
          {isRoot() ? "organisation's" : <strong>{userDept.toUpperCase()}</strong>}{" "}
          knowledge base with natural language queries
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Your question</label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSearch(); }
            }}
            placeholder="What are the governance powers? What is the PTO policy?"
            rows={4}
            className="w-full px-4 py-3 rounded-lg bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring resize-none"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Department — locked for non-root */}
          <div>
            <label className="block text-sm font-medium mb-2 flex items-center gap-1">
              Namespace / Department
              {!isRoot() && <Lock className="w-3 h-3 text-muted-foreground" />}
            </label>
            {isRoot() ? (
              <select
                value={selectedDept}
                onChange={(e) => setSelectedDept(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {ALL_DEPARTMENTS.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            ) : (
              <div className="w-full px-4 py-2.5 rounded-lg bg-muted border border-input text-sm text-muted-foreground capitalize">
                {userDept} (your department)
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Number of results</label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full px-4 py-2.5 rounded-lg bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {[3, 5, 10, 15, 20].map((n) => (
                <option key={n} value={n}>{n} results</option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="w-full md:w-auto px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <><Loader2 className="h-5 w-5 animate-spin" />Searching…</>
          ) : (
            <><Search className="h-5 w-5" />Search</>
          )}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
          <p className="text-destructive">{error}</p>
        </div>
      )}

      {results && (
        <div className="rounded-xl border border-border bg-card">
          <div className="p-4 border-b border-border flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Results</h3>
            <span className="text-xs text-muted-foreground ml-auto capitalize">
              namespace: {isRoot() ? selectedDept : userDept}
            </span>
          </div>
          <div className="p-6">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <div dangerouslySetInnerHTML={{ __html: results.results.replace(/\n/g, "<br />") }} />
            </div>
            {results.sources && results.sources.length > 0 && (
              <div className="mt-6 pt-4 border-t border-border">
                <h4 className="text-sm font-medium mb-2">Sources</h4>
                <div className="flex flex-wrap gap-2">
                  {results.sources.map((source, idx) => (
                    <span key={idx} className="px-2 py-1 text-xs rounded-full bg-primary/10 text-primary">
                      {source.title}{source.page && ` (p.${source.page})`}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default QueryAssistant;
