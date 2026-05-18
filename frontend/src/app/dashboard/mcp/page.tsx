"use client";

import { Plug, Play, Settings, FileSearch, Brain, BarChart3, Layers } from "lucide-react";
import { useState } from "react";

const mcpTools = [
  { id: "document_search", name: "Document Search", icon: FileSearch, status: "active", calls: 1247 },
  { id: "knowledge_retriever", name: "Knowledge Retriever", icon: Brain, status: "active", calls: 892 },
  { id: "content_analyzer", name: "Content Analyzer", icon: BarChart3, status: "active", calls: 456 },
  { id: "batch_processor", name: "Batch Processor", icon: Layers, status: "idle", calls: 78 },
];

export default function MCPDashboardPage() {
  const [selectedTool, setSelectedTool] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Plug className="h-8 w-8 text-indigo-500" />
          MCP Dashboard
        </h1>
        <p className="text-muted-foreground mt-1">
          Model Context Protocol tools and integrations
        </p>
      </div>

      {/* MCP Tools Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {mcpTools.map((tool) => (
          <div
            key={tool.id}
            onClick={() => setSelectedTool(tool.id)}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              selectedTool === tool.id 
                ? 'border-indigo-500 bg-indigo-500/10' 
                : 'border-border bg-card hover:border-indigo-500/50'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <tool.icon className="h-6 w-6 text-indigo-500" />
              <span className={`w-2 h-2 rounded-full ${
                tool.status === 'active' ? 'bg-green-500' : 'bg-gray-500'
              }`}></span>
            </div>
            <h3 className="font-medium">{tool.name}</h3>
            <p className="text-sm text-muted-foreground mt-1">{tool.calls.toLocaleString()} calls</p>
          </div>
        ))}
      </div>

      {/* Tool Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Tool Configuration
          </h2>
          {selectedTool ? (
            <div className="space-y-4">
              <div>
                <label className="text-sm text-muted-foreground">Tool ID</label>
                <input 
                  value={selectedTool}
                  readOnly
                  className="w-full mt-1 p-2 rounded-lg bg-background border border-border"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Department Scope</label>
                <select className="w-full mt-1 p-2 rounded-lg bg-background border border-border">
                  <option>All Departments</option>
                  <option>HR Only</option>
                  <option>Legal Only</option>
                  <option>Finance Only</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Max Results</label>
                <input 
                  type="number"
                  defaultValue={10}
                  className="w-full mt-1 p-2 rounded-lg bg-background border border-border"
                />
              </div>
              <button className="flex items-center gap-2 px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">
                <Play className="h-4 w-4" />
                Test Tool
              </button>
            </div>
          ) : (
            <p className="text-muted-foreground">Select a tool to configure</p>
          )}
        </div>

        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4">Recent Tool Calls</h2>
          <div className="space-y-3">
            {[
              { tool: "Document Search", query: "HR policy vacation", time: "2 min ago" },
              { tool: "Knowledge Retriever", query: "Contract terms", time: "5 min ago" },
              { tool: "Content Analyzer", query: "Q4 report analysis", time: "12 min ago" },
            ].map((call, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-muted/50">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{call.tool}</span>
                  <span className="text-xs text-muted-foreground">{call.time}</span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">"{call.query}"</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
