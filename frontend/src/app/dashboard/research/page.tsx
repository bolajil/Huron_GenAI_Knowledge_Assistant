"use client";

import {
  Microscope,
  Search,
  Globe,
  FileText,
  Sparkles,
  Loader2,
  ExternalLink,
  BookOpen,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useState } from "react";
import { api, InternalResult, WebResult } from "@/services/api";
import { useAuth } from "@/contexts/auth-context";

export default function EnhancedResearchPage() {
  const { user } = useAuth();

  const [query, setQuery] = useState("");
  const [isResearching, setIsResearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Controlled checkbox state
  const [useInternal, setUseInternal] = useState(true);
  const [useWeb, setUseWeb] = useState(true);
  const [useCrossDept, setUseCrossDept] = useState(false);
  const [useAiAnalysis, setUseAiAnalysis] = useState(true);

  // Results
  const [internalResults, setInternalResults] = useState<InternalResult[]>([]);
  const [webResults, setWebResults] = useState<WebResult[]>([]);
  const [synthesis, setSynthesis] = useState("");
  const [hasResults, setHasResults] = useState(false);

  // Collapse state for internal source snippets
  const [expandedInternal, setExpandedInternal] = useState<Set<number>>(new Set());

  const canCrossDept =
    user?.role === "root" || user?.role === "power_user" || user?.role === "dept_admin";

  const handleResearch = async () => {
    if (!query.trim()) return;
    setIsResearching(true);
    setError(null);
    setHasResults(false);
    setInternalResults([]);
    setWebResults([]);
    setSynthesis("");
    setExpandedInternal(new Set());

    try {
      const res = await api.research(query.trim(), {
        use_internal:    useInternal,
        use_web:         useWeb,
        use_cross_dept:  useCrossDept,
        use_ai_analysis: useAiAnalysis,
        dept:            user?.department,
      });
      setInternalResults(res.internal_results ?? []);
      setWebResults(res.web_results ?? []);
      setSynthesis(res.synthesis ?? "");
      setHasResults(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Research failed. Please try again.");
    } finally {
      setIsResearching(false);
    }
  };

  const toggleInternal = (idx: number) => {
    setExpandedInternal((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Microscope className="h-8 w-8 text-purple-500" />
          Enhanced Research
        </h1>
        <p className="text-muted-foreground mt-1">
          Deep research mode with multi-source analysis and web augmentation
        </p>
      </div>

      {/* Query Panel */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-yellow-500" />
          Research Query
        </h2>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleResearch();
          }}
          placeholder="Enter your research topic or question… (Ctrl+Enter to submit)"
          rows={3}
          className="w-full p-4 rounded-lg bg-background border border-border resize-none focus:outline-none focus:ring-2 focus:ring-primary"
        />

        {/* Research Options */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <label className="flex items-center gap-2 p-3 rounded-lg border border-border cursor-pointer hover:bg-accent select-none">
            <input
              type="checkbox"
              checked={useInternal}
              onChange={(e) => setUseInternal(e.target.checked)}
              className="rounded accent-blue-500"
            />
            <FileText className="h-4 w-4 text-blue-500 shrink-0" />
            <span className="text-sm font-medium">Internal Docs</span>
          </label>

          <label className="flex items-center gap-2 p-3 rounded-lg border border-border cursor-pointer hover:bg-accent select-none">
            <input
              type="checkbox"
              checked={useWeb}
              onChange={(e) => setUseWeb(e.target.checked)}
              className="rounded accent-green-500"
            />
            <Globe className="h-4 w-4 text-green-500 shrink-0" />
            <span className="text-sm font-medium">Web Search</span>
          </label>

          <label
            className={`flex items-center gap-2 p-3 rounded-lg border border-border select-none ${
              canCrossDept ? "cursor-pointer hover:bg-accent" : "opacity-40 cursor-not-allowed"
            }`}
          >
            <input
              type="checkbox"
              checked={useCrossDept}
              disabled={!canCrossDept}
              onChange={(e) => setUseCrossDept(e.target.checked)}
              className="rounded accent-orange-500"
            />
            <Search className="h-4 w-4 text-orange-500 shrink-0" />
            <span className="text-sm font-medium">Cross-Dept</span>
          </label>

          <label className="flex items-center gap-2 p-3 rounded-lg border border-border cursor-pointer hover:bg-accent select-none">
            <input
              type="checkbox"
              checked={useAiAnalysis}
              onChange={(e) => setUseAiAnalysis(e.target.checked)}
              className="rounded accent-purple-500"
            />
            <Sparkles className="h-4 w-4 text-purple-500 shrink-0" />
            <span className="text-sm font-medium">AI Analysis</span>
          </label>
        </div>

        <button
          onClick={handleResearch}
          disabled={!query.trim() || isResearching}
          className="mt-4 px-6 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
        >
          {isResearching ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Researching…
            </>
          ) : (
            <>
              <Microscope className="h-4 w-4" />
              Start Research
            </>
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-300 bg-red-50 dark:bg-red-950/30 p-4 text-red-700 dark:text-red-400">
          <AlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Results — only show after at least one search */}
      {hasResults && (
        <>
          {/* Internal + Web Sources */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Internal Sources */}
            <div className="rounded-xl border border-border bg-card p-6">
              <h2 className="font-semibold mb-4 flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-blue-500" />
                Internal Sources
                <span className="ml-auto text-xs text-muted-foreground font-normal">
                  {internalResults.length} result{internalResults.length !== 1 ? "s" : ""}
                </span>
              </h2>

              {internalResults.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {useInternal
                    ? "No internal documents matched this query."
                    : "Internal docs search was not enabled."}
                </p>
              ) : (
                <ul className="space-y-3">
                  {internalResults.map((r, i) => (
                    <li
                      key={i}
                      className={`rounded-lg p-3 border ${
                        r.is_summary
                          ? "border-blue-300 bg-blue-50 dark:bg-blue-950/30"
                          : "border-border bg-background"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium leading-tight">
                          {r.is_summary && (
                            <span className="inline-block mr-1.5 text-xs bg-blue-500 text-white px-1.5 py-0.5 rounded">
                              Summary
                            </span>
                          )}
                          {r.dept && !r.is_summary && (
                            <span className="inline-block mr-1.5 text-xs bg-orange-400 text-white px-1.5 py-0.5 rounded uppercase">
                              {r.dept}
                            </span>
                          )}
                          {r.title}
                        </p>
                        {r.snippet && (
                          <button
                            onClick={() => toggleInternal(i)}
                            className="shrink-0 text-muted-foreground hover:text-foreground"
                          >
                            {expandedInternal.has(i) ? (
                              <ChevronUp className="h-4 w-4" />
                            ) : (
                              <ChevronDown className="h-4 w-4" />
                            )}
                          </button>
                        )}
                      </div>
                      {r.snippet && expandedInternal.has(i) && (
                        <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                          {r.snippet}
                        </p>
                      )}
                      {r.is_summary && r.snippet && (
                        <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                          {r.snippet}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Web Sources */}
            <div className="rounded-xl border border-border bg-card p-6">
              <h2 className="font-semibold mb-4 flex items-center gap-2">
                <Globe className="h-5 w-5 text-green-500" />
                Web Sources
                <span className="ml-auto text-xs text-muted-foreground font-normal">
                  {webResults.length} result{webResults.length !== 1 ? "s" : ""}
                </span>
              </h2>

              {webResults.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {useWeb
                    ? "No web results returned."
                    : "Web search was not enabled."}
                </p>
              ) : (
                <ul className="space-y-3">
                  {webResults.map((r, i) => (
                    <li key={i} className="rounded-lg border border-border bg-background p-3">
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                      >
                        {r.title}
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                      {r.url && (
                        <p className="text-xs text-muted-foreground truncate mt-0.5">{r.url}</p>
                      )}
                      {r.snippet && (
                        <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed line-clamp-3">
                          {r.snippet}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* AI Synthesis */}
          <div className="rounded-xl border border-border bg-card p-6">
            <h2 className="font-semibold mb-4 flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-yellow-500" />
              AI-Synthesized Analysis
            </h2>

            {!useAiAnalysis ? (
              <p className="text-sm text-muted-foreground">AI analysis was not enabled.</p>
            ) : synthesis ? (
              <div className="prose prose-sm dark:prose-invert max-w-none bg-background rounded-lg p-4 text-sm leading-relaxed whitespace-pre-wrap">
                {synthesis}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                AI synthesis was not available for this query.
              </p>
            )}
          </div>
        </>
      )}

      {/* Empty state before first search */}
      {!hasResults && !isResearching && !error && (
        <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground">
          <Microscope className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">
            Enter a research query above and click <strong>Start Research</strong> to begin.
          </p>
        </div>
      )}
    </div>
  );
}
