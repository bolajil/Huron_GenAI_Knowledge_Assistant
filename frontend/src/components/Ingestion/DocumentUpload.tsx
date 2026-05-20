/**
 * Document Upload Component
 * Per FRONTEND_MIGRATION_GUIDE.md - components/Ingestion/DocumentUpload.jsx
 */
"use client";

import { useState, useCallback } from "react";
import {
  Upload,
  FileText,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { api } from "../../services/api";

interface UploadedFile {
  file: File;
  status: "pending" | "uploading" | "success" | "error";
  message?: string;
}

export function DocumentUpload() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [selectedIndex, setSelectedIndex] = useState("default_faiss");
  const [selectedDepartment, setSelectedDepartment] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const availableIndexes = [
    { value: "default_faiss", label: "Default FAISS" },
    { value: "AWS_index", label: "AWS Index" },
    { value: "ByLaw_index", label: "ByLaw Index" },
  ];

  const departments = [
    { value: "", label: "No Department" },
    { value: "hr", label: "Human Resources" },
    { value: "finance", label: "Finance" },
    { value: "legal", label: "Legal" },
    { value: "clinical", label: "Clinical" },
    { value: "it", label: "IT" },
    { value: "operations", label: "Operations" },
  ];

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
    }
  };

  const addFiles = (newFiles: File[]) => {
    const uploadFiles: UploadedFile[] = newFiles.map((file) => ({
      file,
      status: "pending",
    }));
    setFiles((prev) => [...prev, ...uploadFiles]);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const uploadFile = async (index: number) => {
    const uploadedFile = files[index];
    if (!uploadedFile || uploadedFile.status === "uploading") return;

    setFiles((prev) =>
      prev.map((f, i) =>
        i === index ? { ...f, status: "uploading" as const } : f
      )
    );

    try {
      const response = await api.ingestDocument(
        uploadedFile.file,
        selectedIndex,
        selectedDepartment || undefined
      );

      setFiles((prev) =>
        prev.map((f, i) =>
          i === index
            ? { ...f, status: "success" as const, message: response.status }
            : f
        )
      );
    } catch (error) {
      setFiles((prev) =>
        prev.map((f, i) =>
          i === index
            ? {
                ...f,
                status: "error" as const,
                message: error instanceof Error ? error.message : "Upload failed",
              }
            : f
        )
      );
    }
  };

  const uploadAll = async () => {
    for (let i = 0; i < files.length; i++) {
      if (files[i].status === "pending") {
        await uploadFile(i);
      }
    }
  };

  const getFileIcon = (status: UploadedFile["status"]) => {
    switch (status) {
      case "uploading":
        return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
      case "success":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "error":
        return <AlertCircle className="h-5 w-5 text-destructive" />;
      default:
        return <FileText className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const pendingCount = files.filter((f) => f.status === "pending").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Upload className="h-6 w-6 text-primary" />
          Document Ingestion
        </h2>
        <p className="text-muted-foreground mt-1">
          Upload documents to your knowledge base
        </p>
      </div>

      {/* Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Target Index:</label>
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

        <div>
          <label className="block text-sm font-medium mb-2">Department:</label>
          <select
            value={selectedDepartment}
            onChange={(e) => setSelectedDepartment(e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {departments.map((dept) => (
              <option key={dept.value} value={dept.value}>
                {dept.label}
              </option>
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
          dragActive
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50"
        }`}
      >
        <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
        <p className="text-lg font-medium mb-2">
          Drag and drop files here, or click to browse
        </p>
        <p className="text-sm text-muted-foreground mb-4">
          Supports PDF, DOCX, TXT, MD files
        </p>
        <label className="inline-block">
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.txt,.md"
            onChange={handleFileSelect}
            className="hidden"
          />
          <span className="px-4 py-2 bg-primary text-primary-foreground rounded-lg cursor-pointer hover:bg-primary/90 transition-colors">
            Browse Files
          </span>
        </label>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="rounded-xl border border-border bg-card">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h3 className="font-semibold">
              Files ({files.length})
            </h3>
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
            {files.map((uploadedFile, index) => (
              <div
                key={index}
                className="p-4 flex items-center gap-4"
              >
                {getFileIcon(uploadedFile.status)}

                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">
                    {uploadedFile.file.name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {(uploadedFile.file.size / 1024).toFixed(1)} KB
                    {uploadedFile.message && ` • ${uploadedFile.message}`}
                  </p>
                </div>

                {uploadedFile.status === "pending" && (
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
