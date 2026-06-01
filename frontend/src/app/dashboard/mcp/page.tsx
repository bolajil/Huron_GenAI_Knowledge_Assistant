"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plug, Send, Mail, FileDown, BarChart2, Zap, Settings,
  Plus, Trash2, ToggleLeft, ToggleRight, ClipboardList,
  CheckCircle, XCircle, Loader2, ChevronDown, ChevronUp,
  AlertTriangle,
} from "lucide-react";
import { api } from "../../../services/api";
import type { McpTool, McpActionLog } from "../../../services/api";
import { useAuth } from "../../../contexts/auth-context";

const TOOL_ICONS: Record<string, React.ReactNode> = {
  slack:         <Send className="h-5 w-5" />,
  email:         <Mail className="h-5 w-5" />,
  pdf_report:    <FileDown className="h-5 w-5" />,
  data_analyzer: <BarChart2 className="h-5 w-5" />,
};

const CATEGORY_COLORS: Record<string, string> = {
  communication: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  report:        "bg-green-500/15 text-green-600 dark:text-green-400",
  analysis:      "bg-purple-500/15 text-purple-600 dark:text-purple-400",
};

const ROLE_LABELS: Record<string, string> = {
  user:       "All users",
  power_user: "Power users+",
  dept_admin: "Admins+",
  root:       "Root only",
};

// ─── Config modal ─────────────────────────────────────────────────────────────

const TOOL_CONFIG_FIELDS: Record<string, Array<{ key: string; label: string; placeholder: string; sensitive?: boolean }>> = {
  slack: [
    { key: "webhook_url",     label: "Webhook URL",      placeholder: "https://hooks.slack.com/…", sensitive: true },
    { key: "default_channel", label: "Default Channel",  placeholder: "#general" },
  ],
  email: [
    { key: "smtp_host",         label: "SMTP Host",         placeholder: "smtp.gmail.com" },
    { key: "smtp_port",         label: "SMTP Port",         placeholder: "587" },
    { key: "smtp_user",         label: "SMTP Username",     placeholder: "you@gmail.com" },
    { key: "smtp_password",     label: "SMTP Password",     placeholder: "app-password", sensitive: true },
    { key: "from_addr",         label: "From Address",      placeholder: "Huron GenAI <you@gmail.com>" },
    { key: "default_recipient", label: "Default Recipient", placeholder: "team@example.com" },
  ],
};

function ConfigModal({
  tool, deptCode, onClose,
}: { tool: McpTool; deptCode: string; onClose: () => void }) {
  const fields = TOOL_CONFIG_FIELDS[tool.tool_type] ?? [];
  const [values, setValues]   = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const [saved, setSaved]     = useState(false);

  useEffect(() => {
    api.getMcpToolConfig(tool.id, deptCode)
      .then(({ fields: f }) => setValues(f))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [tool.id, deptCode]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.setMcpToolConfig(tool.id, deptCode, values);
      setSaved(true);
      setTimeout(onClose, 800);
    } catch {
      alert("Failed to save configuration.");
    } finally {
      setSaving(false);
    }
  };

  if (fields.length === 0) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md">
          <p className="text-sm text-muted-foreground">
            This tool requires no configuration — it uses shared system credentials.
          </p>
          <button onClick={onClose} className="mt-4 w-full py-2 border border-border rounded-lg text-sm hover:bg-accent">
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl p-6 w-full max-w-lg shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Configure — {tool.name}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground p-1 rounded">
            <XCircle className="h-5 w-5" />
          </button>
        </div>
        <p className="text-xs text-muted-foreground mb-4">
          Credentials are stored encrypted for department: <strong>{deptCode}</strong>
        </p>
        {loading ? (
          <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin" /></div>
        ) : (
          <div className="space-y-3">
            {fields.map((f) => (
              <div key={f.key}>
                <label className="block text-sm font-medium mb-1">{f.label}</label>
                <input
                  type={f.sensitive ? "password" : "text"}
                  value={values[f.key] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                  placeholder={values[f.key] === "***" ? "••••••••" : f.placeholder}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            ))}
          </div>
        )}
        <div className="flex gap-3 mt-6">
          <button
            onClick={handleSave}
            disabled={saving || saved}
            className="flex-1 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-60"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : saved ? <CheckCircle className="h-4 w-4" /> : null}
            {saved ? "Saved!" : saving ? "Saving…" : "Save"}
          </button>
          <button onClick={onClose} className="px-4 py-2 border border-border rounded-lg text-sm hover:bg-accent">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Add Tool form ─────────────────────────────────────────────────────────────

function AddToolForm({ onAdded }: { onAdded: () => void }) {
  const [open, setOpen]         = useState(false);
  const [saving, setSaving]     = useState(false);
  const [form, setForm]         = useState({
    name: "", category: "communication", description: "",
    tool_type: "slack", dept_scope: "", min_role: "user",
  });

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.tool_type.trim()) return;
    setSaving(true);
    try {
      await api.createMcpTool({
        ...form,
        dept_scope: form.dept_scope.trim() || undefined,
      });
      setForm({ name: "", category: "communication", description: "", tool_type: "slack", dept_scope: "", min_role: "user" });
      setOpen(false);
      onAdded();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create tool");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between p-4 hover:bg-accent transition-colors text-left"
      >
        <span className="flex items-center gap-2 font-medium text-sm">
          <Plus className="h-4 w-4" />
          Add New Tool
        </span>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open && (
        <div className="p-4 border-t border-border space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Tool Name *</label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Jira Ticket Creator"
                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Tool Type *</label>
              <input
                value={form.tool_type}
                onChange={(e) => setForm((f) => ({ ...f, tool_type: e.target.value }))}
                placeholder="slack | email | pdf_report | data_analyzer"
                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Description</label>
            <input
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="What does this tool do?"
              className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Category</label>
              <select
                value={form.category}
                onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm focus:outline-none"
              >
                <option value="communication">Communication</option>
                <option value="report">Report</option>
                <option value="analysis">Analysis</option>
                <option value="integration">Integration</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Min Role</label>
              <select
                value={form.min_role}
                onChange={(e) => setForm((f) => ({ ...f, min_role: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm focus:outline-none"
              >
                <option value="user">All users</option>
                <option value="power_user">Power users+</option>
                <option value="dept_admin">Admins+</option>
                <option value="root">Root only</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Dept Scope (optional)</label>
              <input
                value={form.dept_scope}
                onChange={(e) => setForm((f) => ({ ...f, dept_scope: e.target.value }))}
                placeholder="hr,finance (blank = all)"
                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleSubmit}
              disabled={saving || !form.name.trim()}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {saving ? "Creating…" : "Create Tool"}
            </button>
            <button onClick={() => setOpen(false)} className="px-4 py-2 border border-border rounded-lg text-sm hover:bg-accent">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────────

type Tab = "tools" | "logs" | "manage";

export default function MCPDashboardPage() {
  const { user, isDeptAdmin } = useAuth();
  const isAdmin = isDeptAdmin();

  const [tab, setTab]         = useState<Tab>("tools");
  const [tools, setTools]     = useState<McpTool[]>([]);
  const [logs, setLogs]       = useState<McpActionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [configTool, setConfigTool] = useState<McpTool | null>(null);
  const [allTools, setAllTools]     = useState<McpTool[]>([]);

  const loadTools = useCallback(async () => {
    setLoading(true);
    try {
      const { tools: t } = await api.listMcpTools();
      setTools(t);
    } catch {
      // silently ignore — page degrades gracefully
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAllToolsForAdmin = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const { tools: t } = await api.listMcpTools();
      setAllTools(t);
    } catch { /* ignore */ }
  }, [isAdmin]);

  const loadLogs = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const { logs: l } = await api.getMcpLogs(50);
      setLogs(l);
    } catch { /* ignore */ }
  }, [isAdmin]);

  useEffect(() => { loadTools(); }, [loadTools]);
  useEffect(() => {
    if (tab === "logs")   loadLogs();
    if (tab === "manage") loadAllToolsForAdmin();
  }, [tab, loadLogs, loadAllToolsForAdmin]);

  const handleToggle = async (tool: McpTool) => {
    try {
      await api.updateMcpTool(tool.id, { is_enabled: !tool.is_enabled });
      loadAllToolsForAdmin();
      loadTools();
    } catch { /* ignore */ }
  };

  const handleDelete = async (tool: McpTool) => {
    if (!confirm(`Delete "${tool.name}"? This cannot be undone.`)) return;
    try {
      await api.deleteMcpTool(tool.id);
      loadAllToolsForAdmin();
      loadTools();
    } catch { /* ignore */ }
  };

  const TAB_ITEMS: Array<{ key: Tab; label: string; icon: React.ReactNode }> = [
    { key: "tools",  label: "Available Tools",  icon: <Plug className="h-4 w-4" /> },
    ...(isAdmin ? [
      { key: "logs"   as Tab, label: "Action Logs",     icon: <ClipboardList className="h-4 w-4" /> },
      { key: "manage" as Tab, label: "Manage Tools",    icon: <Settings className="h-4 w-4" /> },
    ] : []),
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Plug className="h-8 w-8 text-indigo-500" />
          MCP Dashboard
        </h1>
        <p className="text-muted-foreground mt-1">
          Model Context Protocol — take action on your query results
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {TAB_ITEMS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              tab === t.key
                ? "border-indigo-500 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tools tab ── */}
      {tab === "tools" && (
        <>
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : tools.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground">
              <Zap className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No tools available for your role and department.</p>
              {isAdmin && (
                <p className="text-xs mt-1">Switch to the Manage Tools tab to add some.</p>
              )}
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-border bg-card p-4">
                <p className="text-sm text-muted-foreground">
                  These tools appear as action buttons below your query results. Click a result, then choose an action.
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
                {tools.map((tool) => (
                  <div key={tool.id} className="rounded-xl border border-border bg-card p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-500">
                          {TOOL_ICONS[tool.tool_type] ?? <Zap className="h-5 w-5" />}
                        </div>
                        <div>
                          <h3 className="font-medium">{tool.name}</h3>
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${CATEGORY_COLORS[tool.category] ?? "bg-muted text-muted-foreground"}`}>
                            {tool.category}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {tool.configured ? (
                          <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                            <CheckCircle className="h-3.5 w-3.5" /> Ready
                          </span>
                        ) : tool.tool_type === "pdf_report" || tool.tool_type === "data_analyzer" ? (
                          <span className="text-xs text-green-600 dark:text-green-400">Ready</span>
                        ) : (
                          <span className="flex items-center gap-1 text-xs text-amber-500">
                            <AlertTriangle className="h-3.5 w-3.5" /> Needs setup
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground">{tool.description}</p>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
                      <span className="text-xs text-muted-foreground">
                        {ROLE_LABELS[tool.min_role] ?? tool.min_role}
                        {tool.dept_scope && ` · ${tool.dept_scope}`}
                      </span>
                      {isAdmin && TOOL_CONFIG_FIELDS[tool.tool_type] && (
                        <button
                          onClick={() => setConfigTool(tool)}
                          className="text-xs px-2.5 py-1 rounded border border-border hover:bg-accent transition-colors"
                        >
                          Configure
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}

      {/* ── Logs tab ── */}
      {tab === "logs" && isAdmin && (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="p-4 border-b border-border">
            <h2 className="font-semibold flex items-center gap-2">
              <ClipboardList className="h-5 w-5" />
              Action Log
              <span className="ml-auto text-xs font-normal text-muted-foreground">Last 50 actions</span>
            </h2>
          </div>
          {logs.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">No actions recorded yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left p-3 font-medium">Tool</th>
                    <th className="text-left p-3 font-medium">Dept</th>
                    <th className="text-left p-3 font-medium">Query</th>
                    <th className="text-left p-3 font-medium">Status</th>
                    <th className="text-left p-3 font-medium">When</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} className="border-t border-border hover:bg-muted/30">
                      <td className="p-3 font-medium">{log.tool_name}</td>
                      <td className="p-3 text-muted-foreground uppercase text-xs">{log.dept_code}</td>
                      <td className="p-3 text-muted-foreground max-w-[200px] truncate" title={log.query_snippet}>
                        {log.query_snippet}
                      </td>
                      <td className="p-3">
                        {log.status === "ok" ? (
                          <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                            <CheckCircle className="h-3.5 w-3.5" /> ok
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-destructive" title={log.error_msg ?? ""}>
                            <XCircle className="h-3.5 w-3.5" /> error
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-muted-foreground text-xs">
                        {new Date(log.ran_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Manage tab ── */}
      {tab === "manage" && isAdmin && (
        <div className="space-y-4">
          <AddToolForm onAdded={() => { loadAllToolsForAdmin(); loadTools(); }} />

          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="p-4 border-b border-border">
              <h2 className="font-semibold flex items-center gap-2">
                <Settings className="h-5 w-5" />
                All Tools
              </h2>
            </div>
            {allTools.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">No tools found.</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left p-3 font-medium">Name</th>
                    <th className="text-left p-3 font-medium">Type</th>
                    <th className="text-left p-3 font-medium">Min Role</th>
                    <th className="text-left p-3 font-medium">Scope</th>
                    <th className="text-left p-3 font-medium">Status</th>
                    <th className="text-left p-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {allTools.map((tool) => (
                    <tr key={tool.id} className="border-t border-border hover:bg-muted/30">
                      <td className="p-3 font-medium">{tool.name}</td>
                      <td className="p-3 text-muted-foreground font-mono text-xs">{tool.tool_type}</td>
                      <td className="p-3 text-muted-foreground text-xs">{ROLE_LABELS[tool.min_role] ?? tool.min_role}</td>
                      <td className="p-3 text-muted-foreground text-xs">{tool.dept_scope ?? "Global"}</td>
                      <td className="p-3">
                        {tool.is_enabled ? (
                          <span className="text-xs text-green-600 dark:text-green-400">Enabled</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Disabled</span>
                        )}
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleToggle(tool)}
                            title={tool.is_enabled ? "Disable" : "Enable"}
                            className="text-muted-foreground hover:text-foreground transition-colors"
                          >
                            {tool.is_enabled
                              ? <ToggleRight className="h-5 w-5 text-green-500" />
                              : <ToggleLeft className="h-5 w-5" />}
                          </button>
                          {TOOL_CONFIG_FIELDS[tool.tool_type] && (
                            <button
                              onClick={() => setConfigTool(tool)}
                              title="Configure"
                              className="text-muted-foreground hover:text-foreground transition-colors"
                            >
                              <Settings className="h-4 w-4" />
                            </button>
                          )}
                          {user?.role === "root" && (
                            <button
                              onClick={() => handleDelete(tool)}
                              title="Delete"
                              className="text-muted-foreground hover:text-destructive transition-colors"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Config modal */}
      {configTool && (
        <ConfigModal
          tool={configTool}
          deptCode={user?.department ?? "general"}
          onClose={() => { setConfigTool(null); loadTools(); loadAllToolsForAdmin(); }}
        />
      )}
    </div>
  );
}
