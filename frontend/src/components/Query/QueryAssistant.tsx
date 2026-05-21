"use client";

import { useState } from "react";
import {
  Search, Loader2, FileText, AlertCircle, Lock,
  ThumbsUp, ThumbsDown, ShieldAlert,
} from "lucide-react";
import { api } from "../../services/api";
import type { QueryResponse, SourceGuard } from "../../services/api";
import { useAuth } from "../../contexts/auth-context";

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

// Maps top_k → display label. Also controls LLM max_tokens on the backend.
const DEPTH_OPTIONS = [
  { value: 3,  label: "3 – Quick answer" },
  { value: 5,  label: "5 – Standard (default)" },
  { value: 10, label: "10 – Detailed" },
  { value: 15, label: "15 – Thorough" },
  { value: 20, label: "20 – Comprehensive" },
];

interface ResultState extends QueryResponse {
  queryText: string;
  dept: string;
  rating?: 1 | -1;
}

export function QueryAssistant() {
  const { user, isRoot } = useAuth();
  const userDept = user?.department ?? "general";

  const [query, setQuery]               = useState("");
  const [selectedDept, setSelectedDept] = useState(isRoot() ? "hr" : userDept);
  const [topK, setTopK]                 = useState(5);
  const [loading, setLoading]           = useState(false);
  const [result, setResult]             = useState<ResultState | null>(null);
  const [error, setError]               = useState("");
  const [rating, setRating]             = useState<1 | -1 | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) { setError("Please enter a question"); return; }
    setLoading(true);
    setError("");
    setResult(null);
    setRating(null);
    const dept = isRoot() ? selectedDept : userDept;
    try {
      const data = await api.query(query, dept, topK);
      setResult({ ...data, queryText: query, dept });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (r: 1 | -1) => {
    if (rating !== null || !result) return;
    setRating(r);
    try {
      await api.submitFeedback({
        query:     result.queryText,
        response:  result.results,
        rating:    r,
        source:    result.source ?? "general_knowledge",
        dept_code: result.dept,
      });
    } catch (err) {
      console.error("Feedback submit failed:", err);
    }
  };

  const guard: SourceGuard | undefined = result?.source_guard;

  return (
    <div className="space-y-6">
      {/* Header */}
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

      {/* Search form */}
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
          {/* Department */}
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

          {/* Response depth */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Response depth
              <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                (controls detail &amp; length)
              </span>
            </label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full px-4 py-2.5 rounded-lg bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {DEPTH_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
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

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
          <p className="text-destructive">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="rounded-xl border border-border bg-card">
          {/* Result header */}
          <div className="p-4 border-b border-border flex items-center gap-2 flex-wrap">
            <FileText className="h-5 w-5 text-primary shrink-0" />
            <h3 className="font-semibold">Results</h3>

            {/* Source origin badge */}
            {result.source === "general_knowledge" && (
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-600 dark:text-amber-400 font-medium">
                ⚡ General knowledge
              </span>
            )}
            {result.source === "rag" && (
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-green-500/15 text-green-600 dark:text-green-400 font-medium">
                📄 From knowledge base
              </span>
            )}

            <span className="text-xs text-muted-foreground ml-auto capitalize">
              Namespace: {isRoot() ? selectedDept : userDept}
            </span>
          </div>

          <div className="p-6 space-y-4">
            {/* Response text */}
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <div dangerouslySetInnerHTML={{ __html: result.results.replace(/\n/g, "<br />") }} />
            </div>

            {/* Source guard warning */}
            {guard && !guard.passed && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <ShieldAlert className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-600 dark:text-red-400">
                    Source guard warning
                  </p>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    {guard.warning ??
                      "This response may not be fully grounded in the source documents. Please verify before acting on it."}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Confidence: {Math.round(guard.score * 100)}%
                  </p>
                </div>
              </div>
            )}

            {/* Source guard passed — subtle confidence pill */}
            {guard && guard.passed && result.source === "rag" && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-600 dark:text-green-400">
                  ✓ Source verified · {Math.round(guard.score * 100)}% confidence
                </span>
              </div>
            )}

            {/* Source label for general knowledge */}
            {result.source === "general_knowledge" && result.source_label && (
              <p className="text-xs text-muted-foreground">{result.source_label}</p>
            )}

            {/* Sources list */}
            {result.sources && result.sources.length > 0 && (
              <div className="pt-4 border-t border-border">
                <h4 className="text-sm font-medium mb-2">Sources</h4>
                <div className="flex flex-wrap gap-2">
                  {result.sources.map((source, i) => (
                    <span
                      key={i}
                      className="px-2 py-1 text-xs rounded-full bg-primary/10 text-primary"
                    >
                      {source.title}{source.page != null && ` (p.${source.page})`}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Feedback */}
            <div className="pt-4 border-t border-border flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Was this helpful?</span>
              <button
                onClick={() => handleFeedback(1)}
                disabled={rating !== null}
                title="Helpful"
                className={`p-1.5 rounded-lg transition-colors ${
                  rating === 1
                    ? "text-green-600 bg-green-500/15"
                    : "text-muted-foreground hover:text-green-600 hover:bg-green-500/10"
                } disabled:cursor-default`}
              >
                <ThumbsUp className="h-4 w-4" />
              </button>
              <button
                onClick={() => handleFeedback(-1)}
                disabled={rating !== null}
                title="Not helpful"
                className={`p-1.5 rounded-lg transition-colors ${
                  rating === -1
                    ? "text-red-600 bg-red-500/15"
                    : "text-muted-foreground hover:text-red-600 hover:bg-red-500/10"
                } disabled:cursor-default`}
              >
                <ThumbsDown className="h-4 w-4" />
              </button>
              {rating !== null && (
                <span className="text-sm text-muted-foreground">
                  {rating === 1 ? "Thanks for the feedback!" : "We'll improve this."}
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default QueryAssistant;
