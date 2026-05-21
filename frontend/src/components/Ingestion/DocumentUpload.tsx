"use client";

import { useState, useCallback } from "react";
import { Upload, FileText, X, Loader2, CheckCircle, AlertCircle, Lock } from "lucide-react";
import { api } from "../../services/api";
import { useAuth } from "../../contexts/auth-context";

interface UploadedFile {
  file: File;
  status: "pending" | "uploading" | "success" | "error";
  message?: string;
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

export function DocumentUpload() {
  const { user, isRoot } = useAuth();
  const userDept = user?.department ?? "general";

  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [selectedDept, setSelectedDept] = useState(isRoot() ? "hr" : userDept);
  const [sensitivity, setSensitivity] = useState("internal");
  const [dragActive, setDragActive] = useState(false);

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
    setFiles((prev) => [...prev, ...newFiles.map((file) => ({ file, status: "pending" as const }))]);
  };

  const removeFile = (index: number) => setFiles((prev) => prev.filter((_, i) => i !== index));

  const uploadFile = async (index: number) => {
    const f = files[index];
    if (!f || f.status === "uploading") return;

    setFiles((prev) => prev.map((item, i) => i === index ? { ...item, status: "uploading" } : item));

    try {
      const dept = isRoot() ? selectedDept : userDept;
      const response = await api.ingestDocument(f.file, dept, sensitivity);
      setFiles((prev) =>
        prev.map((item, i) =>
          i === index ? { ...item, status: "success", message: `Ingested to ${dept} namespace` } : item
        )
      );
    } catch (error) {
      setFiles((prev) =>
        prev.map((item, i) =>
          i === index
            ? { ...item, status: "error", message: error instanceof Error ? error.message : "Upload failed" }
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
    if (status === "success") return <CheckCircle className="h-5 w-5 text-green-500" />;
    if (status === "error") return <AlertCircle className="h-5 w-5 text-destructive" />;
    return <FileText className="h-5 w-5 text-muted-foreground" />;
  };

  const pendingCount = files.filter((f) => f.status === "pending").length;

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
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Department — locked for non-root */}
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
        <p className="text-sm text-muted-foreground mb-4">Supports PDF, DOCX, TXT, MD files</p>
        <label className="inline-block">
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.txt,.md"
            onChange={(e) => e.target.files && addFiles(Array.from(e.target.files))}
            className="hidden"
          />
          <span className="px-4 py-2 bg-primary text-primary-foreground rounded-lg cursor-pointer hover:bg-primary/90 transition-colors">
            Browse Files
          </span>
        </label>
      </div>

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
              <div key={index} className="p-4 flex items-center gap-4">
                {getFileIcon(f.status)}
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{f.file.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {(f.file.size / 1024).toFixed(1)} KB
                    {f.message && ` • ${f.message}`}
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
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default DocumentUpload;
