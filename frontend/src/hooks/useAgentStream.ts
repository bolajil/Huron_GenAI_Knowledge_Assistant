// SSE hook for agent step streaming.
// EventSource doesn't support Authorization headers, so the token is
// passed as a query param: /api/v1/agent/stream/{run_id}?token=...
import { useState, useRef, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8004";

export interface AgentStep {
  run_id:               string;
  step_num:             number;
  type:
    | "thought"
    | "tool_call"
    | "tool_result"
    | "permission_denied"
    | "tool_error"
    | "complete"
    | "error"
    | "max_steps";
  timestamp:            string;
  // thought
  content?:             string;
  // tool_call / tool_result / permission_denied / tool_error
  tool?:                string;
  args?:                Record<string, unknown>;
  result?:              unknown;
  count?:               number;
  dept?:                string;
  reason?:              string;
  error?:               string;
  // complete / max_steps
  answer?:              string;
  steps_taken?:         number;
  namespaces_accessed?: string[];
  faithfulness_score?:  number;
  truncated?:           boolean;
  // error / max_steps
  message?:             string;
}

export type AgentStatus = "idle" | "running" | "complete" | "error";

export interface UseAgentStreamReturn {
  steps:    AgentStep[];
  status:   AgentStatus;
  runId:    string | null;
  answer:   string;
  startRun: (query: string, dept?: string, model?: string, maxSteps?: number) => Promise<void>;
  stopRun:  () => Promise<void>;
}

export function useAgentStream(): UseAgentStreamReturn {
  const [steps,  setSteps]  = useState<AgentStep[]>([]);
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [runId,  setRunId]  = useState<string | null>(null);
  const [answer, setAnswer] = useState<string>("");
  const esRef = useRef<EventSource | null>(null);
  const runIdRef = useRef<string | null>(null);

  const startRun = useCallback(async (
    query:    string,
    dept?:    string,
    model     = "gpt-4o-mini",
    maxSteps  = 12,
  ) => {
    const token = localStorage.getItem("auth_token");
    if (!token) return;

    // Reset state
    setSteps([]);
    setAnswer("");
    setStatus("running");
    esRef.current?.close();

    // POST to start the run
    let rid: string;
    try {
      const res = await fetch(`${API}/api/v1/agent/run`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body:    JSON.stringify({ query, dept, model, max_steps: maxSteps }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Failed to start agent run");
      }
      const data = await res.json();
      rid = data.run_id;
    } catch (e) {
      setStatus("error");
      setSteps([{
        run_id: "", step_num: 0, type: "error",
        timestamp: new Date().toISOString(),
        message: e instanceof Error ? e.message : "Failed to start run",
      }]);
      return;
    }

    setRunId(rid);
    runIdRef.current = rid;

    // Subscribe to SSE stream (token in query param — EventSource has no header support)
    const es = new EventSource(`${API}/api/v1/agent/stream/${rid}?token=${encodeURIComponent(token)}`);
    esRef.current = es;

    es.addEventListener("step", (e: MessageEvent) => {
      const step: AgentStep = JSON.parse(e.data);
      setSteps((prev) => [...prev, step]);

      if (step.type === "complete") {
        setAnswer(step.answer || "");
        setStatus("complete");
        es.close();
      }
      if (step.type === "error") {
        setStatus("error");
        es.close();
      }
    });

    es.addEventListener("timeout", () => {
      setStatus("error");
      es.close();
    });

    es.onerror = () => {
      // Only treat as error if we haven't already completed
      setStatus((prev) => prev === "running" ? "error" : prev);
      es.close();
    };
  }, []);

  const stopRun = useCallback(async () => {
    const rid = runIdRef.current;
    esRef.current?.close();
    if (!rid) { setStatus("idle"); return; }

    const token = localStorage.getItem("auth_token");
    try {
      await fetch(`${API}/api/v1/agent/stop/${rid}`, {
        method:  "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch { /* ignore */ }
    setStatus("idle");
  }, []);

  return { steps, status, runId, answer, startRun, stopRun };
}
