"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Search, Loader2, FileText, AlertCircle, Lock,
  ThumbsUp, ThumbsDown, ShieldAlert, Clock, ChevronLeft,
  Trash2,
} from "lucide-react";
import { api } from "../../services/api";
import type { QueryResponse, SourceGuard, Conversation } from "../../services/api";
import { useAuth } from "../../contexts/auth-context";
import ActionBar from "../mcp/ActionBar";

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

  // History sidebar
  const [history, setHistory]           = useState<Conversation[]>([]);
  const [historyOpen, setHistoryOpen]   = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const autoRestored = useRef(false);

  const loadHistory = useCallback(async () => {
    try {
      const { conversations } = await api.listConversations("query");
      setHistory(conversations);

      if (!autoRestored.current && conversations.length > 0) {
        autoRestored.current = true;
        const latest = conversations[0];
        const { messages } = await api.getMessages(latest.id);
        const userMsg      = messages.find((m) => m.role === "user");
        const assistantMsg = messages.find((m) => m.role === "assistant");
        if (userMsg && assistantMsg) {
          setQuery(userMsg.content);
          setResult({
            status:       "ok",
            query:        userMsg.content,
            results:      assistantMsg.content,
            sources:      [],
            source:       (assistantMsg.source as ResultState["source"]) ?? "rag",
            source_label: assistantMsg.source_label,
            queryText:    userMsg.content,
            dept:         latest.dept,
          });
        }
      }
    } catch {
      // silently ignore — history is non-critical
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

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

      // Persist to conversation memory (fire-and-forget — don't block result display)
      saveToHistory(query, data, dept).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const saveToHistory = async (q: string, data: QueryResponse, dept: string) => {
    try {
      const conv = await api.createConversation("query", dept);
      await api.appendMessage(conv.id, "user", q);
      await api.appendMessage(
        conv.id,
        "assistant",
        data.results,
        data.source,
        data.source_label,
      );
      // Refresh history list
      const { conversations } = await api.listConversations("query");
      setHistory(conversations);
    } catch {
      // non-critical
    }
  };

  const loadHistoryItem = async (conv: Conversation) => {
    try {
      const { messages } = await api.getMessages(conv.id);
      const userMsg      = messages.find((m) => m.role === "user");
      const assistantMsg = messages.find((m) => m.role === "assistant");
      if (!userMsg || !assistantMsg) return;

      setQuery(userMsg.content);
      setResult({
        status:       "ok",
        query:        userMsg.content,
        results:      assistantMsg.content,
        sources:      [],
        source:       (assistantMsg.source as ResultState["source"]) ?? "rag",
        source_label: assistantMsg.source_label,
        queryText:    userMsg.content,
        dept:         conv.dept,
      });
      setRating(null);
      setError("");
    } catch {
      setError("Failed to load history item");
    }
  };

  const deleteHistoryItem = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    try {
      await api.deleteConversation(convId);
      setHistory((prev) => prev.filter((c) => c.id !== convId));
    } catch {
      // ignore
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
    <div className="flex gap-4 h-full">
      {/* History sidebar */}
      <div
        className={`flex-shrink-0 transition-all duration-200 ${
          historyOpen ? "w-60" : "w-10"
        }`}
      >
        {historyOpen ? (
          <div className="rounded-xl border border-border bg-card flex flex-col h-full max-h-[calc(100vh-10rem)]">
            <div className="flex items-center justify-between px-3 py-2.5 border-b border-border">
              <div className="flex items-center gap-1.5 text-sm font-medium">
                <Clock className="h-4 w-4 text-muted-foreground" />
                Query History
              </div>
              <button
                onClick={() => setHistoryOpen(false)}
                className="p-1 rounded hover:bg-accent text-muted-foreground"
                title="Collapse"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {loadingHistory ? (
                <div className="flex justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : history.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4 px-2">
                  No saved queries yet
                </p>
              ) : (
                history.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => loadHistoryItem(conv)}
                    className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-accent text-xs group flex items-start justify-between gap-1 transition-colors"
                  >
                    <span className="line-clamp-2 text-foreground/80 leading-relaxed">
                      {conv.title}
                    </span>
                    <button
                      onClick={(e) => deleteHistoryItem(e, conv.id)}
                      className="opacity-0 group-hover:opacity-100 shrink-0 p-0.5 rounded hover:text-destructive transition-all"
                      title="Delete"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </button>
                ))
              )}
            </div>
          </div>
        ) : (
          <button
            onClick={() => setHistoryOpen(true)}
            className="w-10 h-10 flex items-center justify-center rounded-xl border border-border bg-card hover:bg-accent text-muted-foreground"
            title="Show query history"
          >
            <Clock className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Main content */}
      <div className="flex-1 space-y-6 min-w-0">
        {/* Header */}
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Search className="h-6 w-6 text-primary" />
            Query Assistant
          </h2>
          <p className="text-muted-foreground mt-1">
            Search your{" "}
            {isRoot()
              ? "organisation's"
              : <strong>{userDept.toUpperCase()}</strong>}{" "}
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
            <div className="p-4 border-b border-border flex items-center gap-2 flex-wrap">
              <FileText className="h-5 w-5 text-primary shrink-0" />
              <h3 className="font-semibold">Results</h3>

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
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <div dangerouslySetInnerHTML={{ __html: result.results.replace(/\n/g, "<br />") }} />
              </div>

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

              {guard && guard.passed && result.source === "rag" && (
                <div className="flex items-center gap-1.5">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-600 dark:text-green-400">
                    ✓ Source verified · {Math.round(guard.score * 100)}% confidence
                  </span>
                </div>
              )}

              {result.source === "general_knowledge" && result.source_label && (
                <p className="text-xs text-muted-foreground">{result.source_label}</p>
              )}

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
              <ActionBar resultText={result.results} query={result.queryText} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default QueryAssistant;
