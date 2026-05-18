"use client";

import { Database, Plus, Trash2, RefreshCw, HardDrive, FileText } from "lucide-react";
import { useState } from "react";

const mockIndexes = [
  { name: "AWS_index", type: "FAISS", documents: 1247, size: "45 MB", status: "active" },
  { name: "ByLaw_index", type: "FAISS", documents: 89, size: "12 MB", status: "active" },
  { name: "default_faiss", type: "FAISS", documents: 2341, size: "78 MB", status: "active" },
  { name: "HR_Policies", type: "Pinecone", documents: 456, size: "Cloud", status: "active" },
  { name: "Legal_Contracts", type: "Weaviate", documents: 234, size: "Cloud", status: "syncing" },
];

export default function IndexManagementPage() {
  const [indexes] = useState(mockIndexes);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Database className="h-8 w-8 text-cyan-500" />
            Index Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage vector indexes and document collections
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90">
          <Plus className="h-4 w-4" />
          Create Index
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <Database className="h-8 w-8 text-cyan-500" />
            <div>
              <p className="text-2xl font-bold">{indexes.length}</p>
              <p className="text-sm text-muted-foreground">Total Indexes</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <FileText className="h-8 w-8 text-blue-500" />
            <div>
              <p className="text-2xl font-bold">{indexes.reduce((acc, i) => acc + i.documents, 0).toLocaleString()}</p>
              <p className="text-sm text-muted-foreground">Total Documents</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <HardDrive className="h-8 w-8 text-green-500" />
            <div>
              <p className="text-2xl font-bold">135 MB</p>
              <p className="text-sm text-muted-foreground">Local Storage</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <RefreshCw className="h-8 w-8 text-orange-500" />
            <div>
              <p className="text-2xl font-bold">1</p>
              <p className="text-sm text-muted-foreground">Syncing</p>
            </div>
          </div>
        </div>
      </div>

      {/* Index Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-4 font-medium">Index Name</th>
              <th className="text-left p-4 font-medium">Type</th>
              <th className="text-left p-4 font-medium">Documents</th>
              <th className="text-left p-4 font-medium">Size</th>
              <th className="text-left p-4 font-medium">Status</th>
              <th className="text-left p-4 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {indexes.map((index) => (
              <tr key={index.name} className="border-t border-border hover:bg-muted/30">
                <td className="p-4 font-medium">{index.name}</td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded text-xs ${
                    index.type === 'FAISS' ? 'bg-blue-500/10 text-blue-500' :
                    index.type === 'Pinecone' ? 'bg-purple-500/10 text-purple-500' :
                    'bg-green-500/10 text-green-500'
                  }`}>
                    {index.type}
                  </span>
                </td>
                <td className="p-4">{index.documents.toLocaleString()}</td>
                <td className="p-4">{index.size}</td>
                <td className="p-4">
                  <span className={`flex items-center gap-1 ${
                    index.status === 'active' ? 'text-green-500' : 'text-yellow-500'
                  }`}>
                    <span className={`w-2 h-2 rounded-full ${
                      index.status === 'active' ? 'bg-green-500' : 'bg-yellow-500 animate-pulse'
                    }`}></span>
                    {index.status}
                  </span>
                </td>
                <td className="p-4">
                  <div className="flex items-center gap-2">
                    <button className="p-2 hover:bg-accent rounded-lg" title="Refresh">
                      <RefreshCw className="h-4 w-4" />
                    </button>
                    <button className="p-2 hover:bg-red-500/10 text-red-500 rounded-lg" title="Delete">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
