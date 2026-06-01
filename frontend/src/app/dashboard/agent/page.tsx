"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Bot, Play, Square, Search, GitCompare,
  Shield, CheckCircle, AlertTriangle, Clock,
  ChevronLeft, Trash2, Loader2,
} from "lucide-react";
import { useAuth } from "../../../contexts/auth-context";
import { useAgentStream, type AgentStep } from "../../../hooks/useAgentStream";
import { api, type Conversation } from "../../../services/api";

const DEPT_OPTIONS = [
  { code: "hr",         label: "Human Resources" },
  { code: "legal",      label: "Legal" },
  { code: "finance",    label: "Finance" },
  { code: "clinical",   label: "Clinical" },
  { code: "operations", label: "Operations" },
  { code: "it",         label: "IT & Engineering" },
  { code: "marketing",  label: "Marketing" },
  { code: "external",   label: "External" },
];

const EXAMPLE_QUERIES_CROSS = [
  "Does HR overtime policy conflict with Finance expense reimbursement rules?",
  "Summarize what all departments say about data retention and privacy.",
  "What is missing from the Clinical HIPAA documentation compared to Legal requirements?",
  "List every policy that references remote work across all departments.",
];

const EXAMPLE_QUERIES_SINGLE = [
  "What are the overtime rules in this department?",
  "Summarize the key policies for new employees.",
];

// ── Step card ────────────────────────────────────────────────────────────────

const STEP_CFG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  thought: {
    color: "border-blue-400 bg-blue-50 dark:bg-blue-950/20",
    icon:  <span>💭</span>,
    label: "Reasoning",
  },
  tool_call: {
    color: "border-purple-400 bg-purple-50 dark:bg-purple-950/20",
    icon:  <Search className="w-3.5 h-3.5 text-purple-600" />,
    label: "Tool Called",
  },
  tool_result: {
    color: "border-green-400 bg-green-50 dark:bg-green-950/20",
    icon:  <CheckCircle className="w-3.5 h-3.5 text-green-600" />,
    label: "Result",
  },
  permission_denied: {
    color: "border-red-400 bg-red-50 dark:bg-red-950/20",
    icon:  <Shield className="w-3.5 h-3.5 text-red-600" />,
    label: "Access Denied",
  },
  tool_error: {
    color: "border-orange-400 bg-orange-50 dark:bg-orange-950/20",
    icon:  <AlertTriangle className="w-3.5 h-3.5 text-orange-600" />,
    label: "Tool Error",
  },
  complete: {
    color: "border-teal-400 bg-teal-50 dark:bg-teal-950/20",
    icon:  <CheckCircle className="w-3.5 h-3.5 text-teal-600" />,
    label: "Complete",
  },
  max_steps: {
    color: "border-yellow-400 bg-yellow-50 dark:bg-yellow-950/20",
    icon:  <Clock className="w-3.5 h-3.5 text-yellow-600" />,
    label: "Max Steps",
  },
  error: {
    color: "border-red-500 bg-red-50 dark:bg-red-950/20",
    icon:  <AlertTriangle className="w-3.5 h-3.5 text-red-600" />,
    label: "Error",
  },
};

function StepCard({ step }: { step: AgentStep }) {
  const cfg = STEP_CFG[step.type] ?? {
    color: "border-gray-300 bg-gray-50",
    icon:  <span>•</span>,
    label: step.type,
  };

  return (
    <div className={`rounded-lg border-l-4 p-3 mb-2 ${cfg.color}`}>
      <div className="flex items-center gap-2 mb-1">
        {cfg.icon}
        <span className="text-xs font-semibold uppercase tracking-wide opacity-70">
          Step {step.step_num} · {cfg.label}
        </span>
        <span className="text-xs opacity-40 ml-auto">
          {new Date(step.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
        </span>
      </div>

      {step.type === "thought" && (
        <p className="text-sm">{step.content}</p>
      )}

      {step.type === "tool_call" && (
        <p className="text-sm font-mono text-purple-800 dark:text-purple-300">
          {step.tool}({JSON.stringify(step.args)})
        </p>
      )}

      {step.type === "tool_result" && (
        <p className="text-sm">
          Found <strong>{step.count ?? 0}</strong> result{(step.count ?? 0) !== 1 ? "s" : ""}{" "}
          {step.args?.dept ? `in ${String(step.args.dept).toUpperCase()} namespace` : ""}
        </p>
      )}

      {step.type === "permission_denied" && (
        <p className="text-sm text-red-700 dark:text-red-400">
          🔒 {step.reason}
        </p>
      )}

      {step.type === "tool_error" && (
        <p className="text-sm text-orange-700 dark:text-orange-400">{step.error}</p>
      )}

      {step.type === "max_steps" && (
        <p className="text-sm text-yellow-700 dark:text-yellow-400">{step.message}</p>
      )}

      {step.type === "error" && (
        <p className="text-sm text-red-700 dark:text-red-400">{step.message}</p>
      )}

      {step.type === "complete" && (
        <div className="text-sm space-y-1">
          <p className="font-medium">
            {step.steps_taken} step{(step.steps_taken ?? 0) !== 1 ? "s" : ""} completed
            {step.namespaces_accessed && step.namespaces_accessed.length > 0 && (
              <span className="font-normal text-muted-foreground">
                {" · "}Namespaces: {step.namespaces_accessed.join(", ")}
              </span>
            )}
          </p>
          {step.truncated && (
            <p className="text-xs text-yellow-600 dark:text-yellow-400">
              ⚠ Max steps reached — answer may be incomplete
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function AgentPage() {
  const { user, hasPermission } = useAuth();
  const { steps, status, answer, startRun, stopRun } = useAgentStream();

  const [query,    setQuery]    = useState("");
  const [dept,     setDept]     = useState(user?.department ?? "hr");
  const [model,    setModel]    = useState("gpt-4o-mini");
  const [maxSteps, setMaxSteps] = useState(12);

  // History sidebar
  const [history, setHistory]               = useState<Conversation[]>([]);
  const [historyOpen, setHistoryOpen]       = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const autoRestored = useRef(false);

  const loadHistory = useCallback(async () => {
    try {
      const { conversations } = await api.listConversations("agent");
      setHistory(conversations);

      if (!autoRestored.current && conversations.length > 0) {
        autoRestored.current = true;
        const latest = conversations[0];
        const { messages } = await api.getMessages(latest.id);
        const userMsg = messages.find((m) => m.role === "user");
        if (userMsg) setQuery(userMsg.content);
      }
    } catch {
      // non-critical
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  // Save completed run to conversation history
  useEffect(() => {
    if (status === "complete" && answer && query.trim()) {
      (async () => {
        try {
          const conv = await api.createConversation("agent", user?.department);
          await api.appendMessage(conv.id, "user", query);
          await api.appendMessage(conv.id, "assistant", answer);
          const { conversations } = await api.listConversations("agent");
          setHistory(conversations);
        } catch {
          // non-critical
        }
      })();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const loadHistoryItem = async (conv: Conversation) => {
    try {
      const { messages } = await api.getMessages(conv.id);
      const userMsg = messages.find((m) => m.role === "user");
      if (userMsg) setQuery(userMsg.content);
    } catch {
      // ignore
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

  const canCrossDept = hasPermission("cross_dept_query");
  const canRun       = hasPermission("agent") && query.trim().length > 0 && status !== "running";

  const exampleQueries = canCrossDept ? EXAMPLE_QUERIES_CROSS : EXAMPLE_QUERIES_SINGLE;

  const statusBadge = {
    idle:     "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
    running:  "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 animate-pulse",
    complete: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    error:    "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  }[status];

  return (
    <div className="flex gap-3 h-[calc(100vh-8rem)]">

      {/* ── History sidebar ────────────────────────────────────────── */}
      <div className={`flex-shrink-0 transition-all duration-200 ${historyOpen ? "w-56" : "w-10"}`}>
        {historyOpen ? (
          <div className="rounded-xl border border-border bg-card flex flex-col h-full">
            <div className="flex items-center justify-between px-3 py-2.5 border-b border-border">
              <div className="flex items-center gap-1.5 text-sm font-medium">
                <Clock className="h-4 w-4 text-muted-foreground" />
                Run History
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
                  No saved runs yet
                </p>
              ) : (
                history.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => loadHistoryItem(conv)}
                    className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-accent text-xs group flex items-start justify-between gap-1 transition-colors"
                  >
                    <span className="line-clamp-2 text-foreground/80 leading-relaxed">{conv.title}</span>
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
            title="Show run history"
          >
            <Clock className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* ── Left: config panel ─────────────────────────────────────── */}
      <div className="w-80 flex-shrink-0 flex flex-col gap-4 overflow-y-auto">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bot className="w-6 h-6 text-primary" />
            AI Agent
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Multi-step reasoning across knowledge bases
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 space-y-4">

          {/* Query input */}
          <div>
            <label className="text-sm font-medium">Query</label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canRun) startRun(query, dept, model, maxSteps); }
              }}
              rows={4}
              placeholder="Ask a complex question that requires searching the knowledge base…"
              className="mt-1 w-full px-3 py-2 text-sm rounded-lg border border-border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {/* Example queries */}
          <div>
            <p className="text-xs text-muted-foreground mb-1.5">Examples:</p>
            {exampleQueries.map((q) => (
              <button
                key={q}
                onClick={() => setQuery(q)}
                className="w-full text-left text-xs p-2 rounded hover:bg-accent transition-colors mb-1 text-muted-foreground border border-dashed border-border"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Department scope */}
          <div>
            <label className="text-sm font-medium">Department scope</label>
            {canCrossDept ? (
              <select
                value={dept}
                onChange={(e) => setDept(e.target.value)}
                className="mt-1 w-full px-3 py-2 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {DEPT_OPTIONS.map((d) => (
                  <option key={d.code} value={d.code}>{d.label}</option>
                ))}
              </select>
            ) : (
              <div className="mt-1 w-full px-3 py-2 text-sm rounded-lg bg-muted border border-input text-muted-foreground">
                {user?.department?.toUpperCase()} (your department)
              </div>
            )}
            {!canCrossDept && (
              <p className="text-xs text-muted-foreground mt-1">
                🔒 Scoped to your department. Request cross-dept access to search multiple namespaces.
              </p>
            )}
          </div>

          {/* Model + Max Steps */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium">Model</label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="mt-1 w-full px-2 py-1.5 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="gpt-4o-mini">GPT-4o mini</option>
                <option value="gpt-4o">GPT-4o</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium">Max steps</label>
              <select
                value={maxSteps}
                onChange={(e) => setMaxSteps(Number(e.target.value))}
                className="mt-1 w-full px-2 py-1.5 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {[4, 6, 8, 12, 15].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Run / Stop button */}
          {status === "running" ? (
            <button
              onClick={stopRun}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Square className="w-4 h-4" /> Stop Agent
            </button>
          ) : (
            <button
              onClick={() => startRun(query, canCrossDept ? dept : user?.department, model, maxSteps)}
              disabled={!canRun}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
            >
              <Play className="w-4 h-4" /> Run Agent
            </button>
          )}
        </div>
      </div>

      {/* ── Right: execution log + answer ──────────────────────────── */}
      <div className="flex-1 flex flex-col gap-4 overflow-hidden min-w-0">

        {/* Final answer */}
        {answer && (
          <div className="rounded-xl border border-teal-300 bg-teal-50 dark:border-teal-700 dark:bg-teal-950/20 p-5 shrink-0 max-h-64 overflow-y-auto">
            <div className="flex items-center gap-2 mb-3">
              <GitCompare className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <h3 className="font-semibold text-sm text-teal-800 dark:text-teal-300">
                Final Answer
              </h3>
            </div>
            <p className="text-sm whitespace-pre-wrap leading-relaxed">{answer}</p>
          </div>
        )}

        {/* Step log */}
        <div className="flex-1 rounded-xl border border-border bg-card flex flex-col overflow-hidden">
          <div className="p-4 border-b border-border flex items-center justify-between shrink-0">
            <h2 className="font-semibold text-sm">Execution Log</h2>
            <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${statusBadge}`}>
              {status}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {steps.length === 0 ? (
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                <div className="text-center">
                  <Bot className="w-12 h-12 mx-auto mb-3 opacity-20" />
                  <p className="font-medium">Enter a question and click Run Agent.</p>
                  <p className="mt-1 text-xs max-w-xs">
                    The agent will reason step-by-step, calling knowledge base search tools
                    as needed, and show every decision here in real time.
                  </p>
                </div>
              </div>
            ) : (
              steps.map((step, i) => <StepCard key={i} step={step} />)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
