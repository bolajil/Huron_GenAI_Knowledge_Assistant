"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Upload, FileText, X, Loader2, CheckCircle, AlertCircle,
  Lock, History, RotateCcw, Trash2, ChevronDown, ChevronRight,
  FileVideo, FileAudio, FileSpreadsheet, Code2,
} from "lucide-react";
import { api, type DocumentSummary, type DocumentVersion } from "../../services/api";
import { useAuth } from "../../contexts/auth-context";

// ── Types ────────────────────────────────────────────────────────────────────

interface UploadedFile {
  file:     File;
  status:   "pending" | "uploading" | "success" | "error";
  message?: string;
  result?:  {
    document_id:   string;
    version:       string;
    file_type:     string;
    parent_chunks: number;
    warnings:      string[];
  };
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

const SENSITIVITY_LEVELS = [
  { value: "public",       label: "Public" },
  { value: "internal",     label: "Internal" },
  { value: "confidential", label: "Confidential" },
  { value: "restricted",   label: "Restricted" },
];

const FILE_TYPE_ACCEPT =
  ".pdf,.docx,.doc,.pptx,.ppt,.xlsx,.xls,.csv,.txt,.md,.html,.json,.mp4,.mkv,.avi,.mov,.mp3,.wav,.m4a";

function fileTypeIcon(fileType: string) {
  if (fileType === "video") return <FileVideo className="h-4 w-4 text-purple-500" />;
  if (fileType === "audio") return <FileAudio className="h-4 w-4 text-pink-500" />;
  if (fileType === "xlsx" || fileType === "csv") return <FileSpreadsheet className="h-4 w-4 text-green-500" />;
  if (fileType === "json" || fileType === "html") return <Code2 className="h-4 w-4 text-orange-500" />;
  return <FileText className="h-4 w-4 text-blue-500" />;
}

function formatDate(iso: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

// ── Version History Panel ────────────────────────────────────────────────────

function VersionHistoryPanel({ dept }: { dept: string }) {
  const [documents, setDocuments]   = useState<DocumentSummary[]>([]);
  const [loading, setLoading]       = useState(false);
  const [expanded, setExpanded]     = useState<string | null>(null);
  const [versions, setVersions]     = useState<Record<string, DocumentVersion[]>>({});
  const [actionMsg, setActionMsg]   = useState<string>("");

  const loadDocuments = useCallback(async () => {
    if (!dept) return;
    setLoading(true);
    try {
      const res = await api.listDocuments(dept);
      setDocuments(res.documents);
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [dept]);

  useEffect(() => { loadDocuments(); }, [loadDocuments]);

  const toggleDoc = async (docId: string) => {
    if (expanded === docId) { setExpanded(null); return; }
    setExpanded(docId);
    if (!versions[docId]) {
      try {
        const res = await api.getDocumentVersions(dept, docId);
        setVersions((prev) => ({ ...prev, [docId]: res.versions }));
      } catch {
        setVersions((prev) => ({ ...prev, [docId]: [] }));
      }
    }
  };

  const handleRollback = async (docId: string, version: string) => {
    if (!confirm(`Roll back "${docId}" to version ${version}?`)) return;
    try {
      await api.rollbackDocument(dept, docId, version);
      setActionMsg(`Rolled back to ${version}`);
      setVersions((prev) => ({ ...prev, [docId]: [] })); // force reload on next expand
      loadDocuments();
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Rollback failed");
    }
    setTimeout(() => setActionMsg(""), 3000);
  };

  const handleDelete = async (docId: string) => {
    if (!confirm(`Delete ALL versions of "${docId}" from Pinecone and the DB? This cannot be undone.`)) return;
    try {
      const res = await api.deleteDocument(dept, docId);
      setActionMsg(`Deleted ${res.deleted_chunks} chunks`);
      loadDocuments();
      if (expanded === docId) setExpanded(null);
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Delete failed");
    }
    setTimeout(() => setActionMsg(""), 3000);
  };

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2">
          <History className="h-4 w-4 text-primary" />
          Indexed Documents — {dept.toUpperCase()}
        </h3>
        <button
          onClick={loadDocuments}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Refresh
        </button>
      </div>

      {actionMsg && (
        <div className="px-4 py-2 bg-teal-50 dark:bg-teal-950/20 text-teal-700 dark:text-teal-300 text-sm border-b border-teal-200 dark:border-teal-800">
          ✓ {actionMsg}
        </div>
      )}

      <div className="divide-y divide-border">
        {loading ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
            Loading documents…
          </div>
        ) : documents.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            No documents indexed in {dept.toUpperCase()} yet.
          </div>
        ) : (
          documents.map((doc) => (
            <div key={doc.doc_id}>
              {/* Document row */}
              <div className="p-4 flex items-center gap-3 hover:bg-accent/30 transition-colors">
                <button
                  onClick={() => toggleDoc(doc.doc_id)}
                  className="flex items-center gap-2 flex-1 min-w-0 text-left"
                >
                  {expanded === doc.doc_id
                    ? <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                    : <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />}
                  {fileTypeIcon(doc.file_type)}
                  <div className="min-w-0">
                    <p className="font-medium text-sm truncate">{doc.source_file}</p>
                    <p className="text-xs text-muted-foreground">
                      ID: <code className="text-xs">{doc.doc_id}</code>
                      {" · "}{doc.chunk_count} chunks
                      {" · "}Effective {formatDate(doc.effective_date)}
                    </p>
                  </div>
                </button>

                <span className="text-xs px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 shrink-0">
                  v{doc.version}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300 shrink-0">
                  latest
                </span>
                <button
                  onClick={() => handleDelete(doc.doc_id)}
                  className="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-muted-foreground hover:text-red-600 transition-colors shrink-0"
                  title="Delete all versions"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              {/* Version history (expanded) */}
              {expanded === doc.doc_id && (
                <div className="bg-muted/30 border-t border-border px-4 pb-3 pt-2">
                  {!versions[doc.doc_id] ? (
                    <p className="text-xs text-muted-foreground py-2">Loading versions…</p>
                  ) : versions[doc.doc_id].length === 0 ? (
                    <p className="text-xs text-muted-foreground py-2">No version history found.</p>
                  ) : (
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-muted-foreground border-b border-border">
                          <th className="text-left py-1.5 pr-4">Version</th>
                          <th className="text-left py-1.5 pr-4">File</th>
                          <th className="text-left py-1.5 pr-4">Chunks</th>
                          <th className="text-left py-1.5 pr-4">Ingested</th>
                          <th className="text-left py-1.5 pr-4">Status</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {versions[doc.doc_id].map((v) => (
                          <tr key={v.version} className="border-b border-border/50 last:border-0">
                            <td className="py-1.5 pr-4 font-mono">{v.version}</td>
                            <td className="py-1.5 pr-4 truncate max-w-[160px]">{v.source_file}</td>
                            <td className="py-1.5 pr-4">{v.chunk_count}</td>
                            <td className="py-1.5 pr-4">{formatDate(v.ingested_at)}</td>
                            <td className="py-1.5 pr-4">
                              {v.is_latest ? (
                                <span className="text-green-600 font-medium">● current</span>
                              ) : (
                                <span className="text-muted-foreground">○ archived</span>
                              )}
                            </td>
                            <td className="py-1.5">
                              {!v.is_latest && (
                                <button
                                  onClick={() => handleRollback(doc.doc_id, v.version)}
                                  className="flex items-center gap-1 text-blue-600 hover:text-blue-700 dark:text-blue-400"
                                >
                                  <RotateCcw className="h-3 w-3" /> Restore
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export function DocumentUpload() {
  const { user, isRoot } = useAuth();
  const userDept = user?.department ?? "general";

  const [files, setFiles]           = useState<UploadedFile[]>([]);
  const [selectedDept, setSelectedDept] = useState(isRoot() ? "hr" : userDept);
  const [sensitivity, setSensitivity]   = useState("internal");
  const [docId, setDocId]           = useState("");
  const [version, setVersion]       = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    addFiles(Array.from(e.dataTransfer.files));
  }, []);

  const addFiles = (newFiles: File[]) => {
    setFiles((prev) => [
      ...prev,
      ...newFiles.map((file) => ({ file, status: "pending" as const })),
    ]);
  };

  const removeFile = (index: number) =>
    setFiles((prev) => prev.filter((_, i) => i !== index));

  const uploadFile = async (index: number) => {
    const f = files[index];
    if (!f || f.status === "uploading") return;

    setFiles((prev) =>
      prev.map((item, i) => (i === index ? { ...item, status: "uploading" } : item))
    );

    try {
      const dept     = isRoot() ? selectedDept : userDept;
      const response = await api.ingestDocument(f.file, dept, sensitivity, docId, version);
      setFiles((prev) =>
        prev.map((item, i) =>
          i === index
            ? {
                ...item,
                status: "success",
                message: `v${response.version} · ${response.parent_chunks} chunks → ${dept}`,
                result: {
                  document_id:   response.document_id,
                  version:       response.version,
                  file_type:     response.file_type,
                  parent_chunks: response.parent_chunks,
                  warnings:      response.warnings,
                },
              }
            : item
        )
      );
      setRefreshKey((k) => k + 1); // trigger version history reload
    } catch (error) {
      setFiles((prev) =>
        prev.map((item, i) =>
          i === index
            ? {
                ...item,
                status: "error",
                message: error instanceof Error ? error.message : "Upload failed",
              }
            : item
        )
      );
    }
  };

  const uploadAll = async () => {
    for (let i = 0; i < files.length; i++) {
      if (files[i].status === "pending") await uploadFile(i);
    }
  };

  const getFileIcon = (status: UploadedFile["status"]) => {
    if (status === "uploading") return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
    if (status === "success")   return <CheckCircle className="h-5 w-5 text-green-500" />;
    if (status === "error")     return <AlertCircle className="h-5 w-5 text-destructive" />;
    return <FileText className="h-5 w-5 text-muted-foreground" />;
  };

  const pendingCount = files.filter((f) => f.status === "pending").length;
  const activeDept   = isRoot() ? selectedDept : userDept;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Upload className="h-6 w-6 text-primary" />
          Document Ingestion
        </h2>
        <p className="text-muted-foreground mt-1">
          Upload documents to{" "}
          {isRoot()
            ? "any department namespace"
            : <><strong className="capitalize">{userDept}</strong> namespace</>}
          {" "}— versioning is automatic.
        </p>
      </div>

      {/* Config row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2 flex items-center gap-1">
            Target Namespace
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
          <label className="block text-sm font-medium mb-2">Sensitivity Level</label>
          <select
            value={sensitivity}
            onChange={(e) => setSensitivity(e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {SENSITIVITY_LEVELS.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Optional versioning overrides */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">
            Document ID <span className="text-muted-foreground font-normal">(optional — auto-derived from filename)</span>
          </label>
          <input
            type="text"
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
            placeholder="e.g. hr_employee_benefits"
            className="w-full px-4 py-2.5 rounded-lg bg-background border border-input text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Version <span className="text-muted-foreground font-normal">(optional — defaults to YYYY-MM)</span>
          </label>
          <input
            type="text"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="e.g. 2025-01"
            className="w-full px-4 py-2.5 rounded-lg bg-background border border-input text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      </div>

      {/* Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          dragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
        }`}
      >
        <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
        <p className="text-lg font-medium mb-2">Drag and drop files here, or click to browse</p>
        <p className="text-sm text-muted-foreground mb-4">
          PDF · DOCX · PPTX · XLSX · CSV · TXT · HTML · JSON · MP4 · MP3
        </p>
        <label className="inline-block">
          <input
            type="file"
            multiple
            accept={FILE_TYPE_ACCEPT}
            onChange={(e) => e.target.files && addFiles(Array.from(e.target.files))}
            className="hidden"
          />
          <span className="px-4 py-2 bg-primary text-primary-foreground rounded-lg cursor-pointer hover:bg-primary/90 transition-colors">
            Browse Files
          </span>
        </label>
      </div>

      {/* File queue */}
      {files.length > 0 && (
        <div className="rounded-xl border border-border bg-card">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h3 className="font-semibold">Files ({files.length})</h3>
            {pendingCount > 0 && (
              <button
                onClick={uploadAll}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:bg-primary/90 transition-colors"
              >
                Upload All ({pendingCount})
              </button>
            )}
          </div>
          <div className="divide-y divide-border">
            {files.map((f, index) => (
              <div key={index} className="p-4">
                <div className="flex items-center gap-4">
                  {getFileIcon(f.status)}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{f.file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(f.file.size / 1024).toFixed(1)} KB
                      {f.message && <> · {f.message}</>}
                    </p>
                  </div>
                  {f.status === "pending" && (
                    <button
                      onClick={() => uploadFile(index)}
                      className="px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-sm hover:bg-primary/90 transition-colors"
                    >
                      Upload
                    </button>
                  )}
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                {/* Version result badge */}
                {f.status === "success" && f.result && (
                  <div className="mt-2 ml-9 flex flex-wrap gap-2">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300">
                      doc_id: {f.result.document_id}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                      version: {f.result.version}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
                      type: {f.result.file_type}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                      {f.result.parent_chunks} chunks
                    </span>
                    {f.result.warnings.length > 0 && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300">
                        ⚠ {f.result.warnings.length} warning{f.result.warnings.length > 1 ? "s" : ""}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Version history panel */}
      <VersionHistoryPanel key={`${activeDept}-${refreshKey}`} dept={activeDept} />
    </div>
  );
}

export default DocumentUpload;
