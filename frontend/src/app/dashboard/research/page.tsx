"use client";

import { Microscope, Search, Globe, FileText, Sparkles } from "lucide-react";
import { useState } from "react";

export default function EnhancedResearchPage() {
  const [query, setQuery] = useState("");
  const [isResearching, setIsResearching] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Microscope className="h-8 w-8 text-purple-500" />
          Enhanced Research
        </h1>
        <p className="text-muted-foreground mt-1">
          Deep research mode with multi-source analysis and web augmentation
        </p>
      </div>

      {/* Research Input */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-yellow-500" />
          Research Query
        </h2>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your research topic or question..."
          className="w-full h-24 p-4 rounded-lg bg-background border border-border resize-none focus:outline-none focus:ring-2 focus:ring-primary"
        />
        
        {/* Research Options */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <label className="flex items-center gap-2 p-3 rounded-lg border border-border cursor-pointer hover:bg-accent">
            <input type="checkbox" defaultChecked className="rounded" />
            <FileText className="h-4 w-4 text-blue-500" />
            <span className="text-sm">Internal Docs</span>
          </label>
          <label className="flex items-center gap-2 p-3 rounded-lg border border-border cursor-pointer hover:bg-accent">
            <input type="checkbox" defaultChecked className="rounded" />
            <Globe className="h-4 w-4 text-green-500" />
            <span className="text-sm">Web Search</span>
          </label>
          <label className="flex items-center gap-2 p-3 rounded-lg border border-border cursor-pointer hover:bg-accent">
            <input type="checkbox" className="rounded" />
            <Search className="h-4 w-4 text-orange-500" />
            <span className="text-sm">Cross-Dept</span>
          </label>
          <label className="flex items-center gap-2 p-3 rounded-lg border border-border cursor-pointer hover:bg-accent">
            <input type="checkbox" className="rounded" />
            <Sparkles className="h-4 w-4 text-purple-500" />
            <span className="text-sm">AI Analysis</span>
          </label>
        </div>

        <button
          onClick={() => setIsResearching(!isResearching)}
          disabled={!query}
          className="mt-4 px-6 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg font-medium disabled:opacity-50 flex items-center gap-2"
        >
          <Microscope className="h-4 w-4" />
          {isResearching ? 'Researching...' : 'Start Research'}
        </button>
      </div>

      {/* Research Results */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4">Internal Sources</h2>
          <div className="space-y-3">
            <p className="text-muted-foreground text-sm">Research results from internal documents will appear here...</p>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4">Web Sources</h2>
          <div className="space-y-3">
            <p className="text-muted-foreground text-sm">Research results from web search will appear here...</p>
          </div>
        </div>
      </div>

      {/* Synthesized Analysis */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-yellow-500" />
          AI-Synthesized Analysis
        </h2>
        <div className="bg-background rounded-lg p-4 min-h-[200px]">
          <p className="text-muted-foreground">Synthesized research analysis will appear here...</p>
        </div>
      </div>
    </div>
  );
}
