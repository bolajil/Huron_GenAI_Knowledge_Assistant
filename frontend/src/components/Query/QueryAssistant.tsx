/**
 * Query Assistant Component
 * Per FRONTEND_MIGRATION_GUIDE.md - components/Query/QueryAssistant.jsx
 */
"use client";

import { useState } from "react";
import { Search, Loader2, FileText, AlertCircle } from "lucide-react";
import { api } from "../../services/api";

interface QueryResult {
  status: string;
  query: string;
  results: string;
  sources: Array<{ title: string; page?: number }>;
}

export function QueryAssistant() {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState("default_faiss");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<QueryResult | null>(null);
  const [error, setError] = useState("");

  const availableIndexes = [
    { value: "default_faiss", label: "Default FAISS" },
    { value: "AWS_index", label: "AWS Index" },
    { value: "ByLaw_index", label: "ByLaw Index" },
  ];

  const handleSearch = async () => {
    if (!query.trim()) {
      setError("Please enter a question");
      return;
    }

    setLoading(true);
    setError("");
    setResults(null);

    try {
      const response = await api.query(query, selectedIndex, topK);
      setResults(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Search className="h-6 w-6 text-primary" />
          Query Assistant
        </h2>
        <p className="text-muted-foreground mt-1">
          Search your knowledge base with natural language queries
        </p>
      </div>

      {/* Query Form */}
      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        {/* Query Input */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Enter your question:
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="What are the governance powers? What is the PTO policy?"
            rows={4}
            className="w-full px-4 py-3 rounded-lg bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring resize-none"
          />
        </div>

        {/* Options Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Index Selector */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Select Index:
            </label>
            <select
              value={selectedIndex}
              onChange={(e) => setSelectedIndex(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {availableIndexes.map((idx) => (
                <option key={idx.value} value={idx.value}>
                  {idx.label}
                </option>
              ))}
            </select>
          </div>

          {/* Top K */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Number of results:
            </label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full px-4 py-2.5 rounded-lg bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {[3, 5, 10, 15, 20].map((n) => (
                <option key={n} value={n}>
                  {n} results
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Search Button */}
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="w-full md:w-auto px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Searching...
            </>
          ) : (
            <>
              <Search className="h-5 w-5" />
              Search
            </>
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
      {results && (
        <div className="rounded-xl border border-border bg-card">
          <div className="p-4 border-b border-border flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Results</h3>
            <span className="text-sm text-muted-foreground ml-auto">
              Index: {selectedIndex}
            </span>
          </div>
          <div className="p-6">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <div
                dangerouslySetInnerHTML={{
                  __html: results.results.replace(/\n/g, "<br />"),
                }}
              />
            </div>

            {/* Sources */}
            {results.sources && results.sources.length > 0 && (
              <div className="mt-6 pt-4 border-t border-border">
                <h4 className="text-sm font-medium mb-2">Sources:</h4>
                <div className="flex flex-wrap gap-2">
                  {results.sources.map((source, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 text-xs rounded-full bg-primary/10 text-primary"
                    >
                      {source.title}
                      {source.page && ` (p.${source.page})`}
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
