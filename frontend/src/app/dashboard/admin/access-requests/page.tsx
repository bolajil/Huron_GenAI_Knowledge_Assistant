"use client";

import { useEffect, useState, useCallback } from "react";
import {
  ClipboardList,
  CheckCircle2,
  XCircle,
  Clock,
  Send,
  Loader2,
  ShieldAlert,
  Filter,
} from "lucide-react";
import { useAuth } from "../../../../contexts/auth-context";
import { api } from "../../../../services/api";
import type { AccessRequest } from "../../../../services/api";

type StatusFilter = "all" | "pending" | "approved" | "rejected";

const STATUS_STYLE: Record<AccessRequest["status"], { icon: React.ReactNode; cls: string }> = {
  pending:  { icon: <Clock className="w-3.5 h-3.5" />,         cls: "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400" },
  approved: { icon: <CheckCircle2 className="w-3.5 h-3.5" />,  cls: "bg-green-500/10 text-green-600 dark:text-green-400" },
  rejected: { icon: <XCircle className="w-3.5 h-3.5" />,       cls: "bg-red-500/10 text-red-600 dark:text-red-400" },
};

function StatusBadge({ status }: { status: AccessRequest["status"] }) {
  const { icon, cls } = STATUS_STYLE[status];
  return (
    <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {icon}
      {status}
    </span>
  );
}

function timeAgo(timestamp: string): string {
  const diff = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function AccessRequestsPage() {
  const { isDeptAdmin } = useAuth();

  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [tabs, setTabs] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [error, setError] = useState("");

  // Submit form state
  const [showSubmit, setShowSubmit] = useState(false);
  const [selectedTab, setSelectedTab] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState("");

  const fetchRequests = useCallback(async () => {
    try {
      const filter = statusFilter === "all" ? undefined : statusFilter;
      const [reqRes, tabsRes] = await Promise.all([
        api.listAccessRequests(filter),
        api.listRequestableTabs(),
      ]);
      setRequests(reqRes.requests ?? []);
      setTabs(tabsRes.tabs ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load requests");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTab || !reason.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await api.submitAccessRequest(selectedTab, reason.trim());
      setSubmitSuccess(`Request for "${selectedTab}" submitted successfully.`);
      setSelectedTab("");
      setReason("");
      setShowSubmit(false);
      await fetchRequests();
      setTimeout(() => setSubmitSuccess(""), 4000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit request");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReview = async (id: number, action: "approve" | "reject") => {
    setActionLoading(id);
    setError("");
    try {
      await api.reviewAccessRequest(id, action);
      await fetchRequests();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review action failed");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ClipboardList className="w-6 h-6 text-primary" />
            Access Requests
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Request additional tab access or review pending requests.
          </p>
        </div>
        <button
          onClick={() => setShowSubmit(!showSubmit)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Send className="w-4 h-4" />
          New Request
        </button>
      </div>

      {/* Success message */}
      {submitSuccess && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-green-600 dark:text-green-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {submitSuccess}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-600 dark:text-red-400 text-sm flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Submit form */}
      {showSubmit && (
        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-border bg-card p-6 space-y-4"
        >
          <h2 className="font-semibold flex items-center gap-2">
            <Send className="w-4 h-4" /> Request Access
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-muted-foreground mb-1">
                Tab / Feature
              </label>
              <select
                required
                value={selectedTab}
                onChange={(e) => setSelectedTab(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="">Select a tab…</option>
                {tabs.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-muted-foreground mb-1">
                Reason
              </label>
              <input
                type="text"
                required
                placeholder="Brief business justification…"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
          </div>

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={() => { setShowSubmit(false); setSelectedTab(""); setReason(""); }}
              className="px-4 py-2 rounded-lg border border-border text-sm hover:bg-accent transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !selectedTab || !reason.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Submit Request
            </button>
          </div>
        </form>
      )}

      {/* Filter tabs */}
      <div className="flex items-center gap-1 bg-muted/40 rounded-xl p-1 w-fit">
        <Filter className="w-3.5 h-3.5 text-muted-foreground ml-2 mr-1" />
        {(["all", "pending", "approved", "rejected"] as StatusFilter[]).map((f) => (
          <button
            key={f}
            onClick={() => setStatusFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
              statusFilter === f
                ? "bg-background shadow text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Requests list */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40 gap-2 text-muted-foreground">
            <Loader2 className="w-5 h-5 animate-spin" />
            Loading…
          </div>
        ) : requests.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
            <ClipboardList className="w-8 h-8" />
            <p className="text-sm">No requests found</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/40">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">User</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Tab</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Reason</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Submitted</th>
                {isDeptAdmin() && (
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">
                    Actions
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {requests.map((req) => (
                <tr key={req.id} className="hover:bg-accent/30 transition-colors">
                  <td className="px-4 py-3 font-medium">{req.username}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded bg-primary/10 text-primary text-xs">
                      {req.requested_tab}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground max-w-xs truncate">
                    {req.reason}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={req.status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {timeAgo(req.created_at)}
                  </td>
                  {isDeptAdmin() && (
                    <td className="px-4 py-3 text-right">
                      {req.status === "pending" && (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleReview(req.id, "approve")}
                            disabled={actionLoading === req.id}
                            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 hover:bg-green-500/20 text-xs font-medium disabled:opacity-50 transition-colors"
                          >
                            {actionLoading === req.id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <CheckCircle2 className="w-3.5 h-3.5" />
                            )}
                            Approve
                          </button>
                          <button
                            onClick={() => handleReview(req.id, "reject")}
                            disabled={actionLoading === req.id}
                            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-red-500/10 text-red-600 dark:text-red-400 hover:bg-red-500/20 text-xs font-medium disabled:opacity-50 transition-colors"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            Reject
                          </button>
                        </div>
                      )}
                      {req.status !== "pending" && (
                        <span className="text-xs text-muted-foreground">
                          by {req.reviewed_by ?? "—"}
                        </span>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
