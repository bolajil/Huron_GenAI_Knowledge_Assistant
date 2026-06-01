"use client";

import { useState } from "react";
import { X, Loader2, CheckCircle, AlertCircle, Download } from "lucide-react";
import { api } from "../../services/api";
import type { McpTool, McpRunResult } from "../../services/api";

interface Props {
  tool: McpTool;
  resultText: string;
  query: string;
  onClose: () => void;
}

const TOOL_FIELDS: Record<string, Array<{ key: string; label: string; placeholder: string; required?: boolean }>> = {
  slack:         [{ key: "channel",       label: "Slack Channel (optional)",    placeholder: "#general" }],
  email:         [
    { key: "recipient", label: "Recipient Email",         placeholder: "team@example.com", required: true },
    { key: "subject",   label: "Subject (optional)",      placeholder: "Query Result" },
  ],
  pdf_report:    [{ key: "title",         label: "Report Title (optional)",     placeholder: "Knowledge Base Report" }],
  data_analyzer: [{ key: "analysis_type", label: "Analysis Focus (optional)",   placeholder: "trends, patterns, key insights" }],
};

export default function ActionModal({ tool, resultText, query, onClose }: Props) {
  const fields  = TOOL_FIELDS[tool.tool_type] ?? [];
  const [params, setParams]   = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<(McpRunResult & { ok: boolean }) | null>(null);

  const handleRun = async () => {
    const required = fields.filter((f) => f.required && !params[f.key]?.trim());
    if (required.length) {
      alert(`Please fill in: ${required.map((f) => f.label).join(", ")}`);
      return;
    }
    setLoading(true);
    try {
      const res = await api.runMcpAction({
        tool_id:     tool.id,
        result_text: resultText,
        query,
        user_params: params,
      });
      setResult({ ...res, ok: true });
    } catch (err) {
      setResult({
        status: "error",
        detail: err instanceof Error ? err.message : "Action failed",
        ok:     false,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result?.content_base64 || !result.filename) return;
    const bytes = atob(result.content_base64);
    const arr   = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    const blob = new Blob([arr], { type: "application/pdf" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url;
    a.download = result.filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">{tool.name}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground p-1 rounded">
            <X className="h-5 w-5" />
          </button>
        </div>

        {!result ? (
          <>
            <p className="text-sm text-muted-foreground mb-4">{tool.description}</p>

            {!tool.configured && tool.tool_type !== "pdf_report" && tool.tool_type !== "data_analyzer" && (
              <div className="mb-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400 text-xs">
                This tool needs admin configuration before it can be used.
              </div>
            )}

            <div className="space-y-3">
              {fields.map((f) => (
                <div key={f.key}>
                  <label className="block text-sm font-medium mb-1">
                    {f.label}
                    {f.required && <span className="text-destructive ml-1">*</span>}
                  </label>
                  <input
                    type={f.key === "recipient" ? "email" : "text"}
                    value={params[f.key] ?? ""}
                    onChange={(e) => setParams((p) => ({ ...p, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
              ))}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleRun}
                disabled={loading}
                className="flex-1 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <><Loader2 className="h-4 w-4 animate-spin" />Running…</>
                ) : (
                  "Run"
                )}
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2 border border-border rounded-lg text-sm hover:bg-accent transition-colors"
              >
                Cancel
              </button>
            </div>
          </>
        ) : (
          <div className="text-center space-y-4 py-2">
            {result.ok ? (
              <CheckCircle className="h-12 w-12 text-green-500 mx-auto" />
            ) : (
              <AlertCircle className="h-12 w-12 text-destructive mx-auto" />
            )}
            <div>
              <p className="font-medium text-sm">{result.ok ? "Success" : "Failed"}</p>
              <p className="text-sm text-muted-foreground mt-1">{result.detail}</p>
            </div>
            {result.analysis && (
              <div className="text-left rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground max-h-48 overflow-y-auto whitespace-pre-wrap">
                {result.analysis}
              </div>
            )}
            {result.content_base64 && (
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 mx-auto px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:bg-primary/90 transition-colors"
              >
                <Download className="h-4 w-4" />
                Download {result.filename}
              </button>
            )}
            <button
              onClick={onClose}
              className="w-full py-2 border border-border rounded-lg text-sm hover:bg-accent transition-colors"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
