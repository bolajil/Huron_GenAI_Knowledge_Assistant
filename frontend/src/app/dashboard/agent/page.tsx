"use client";

import { Bot, Play, Pause, RotateCcw, Settings, Zap } from "lucide-react";
import { useState } from "react";

export default function AgentAssistantPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [query, setQuery] = useState("");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Bot className="h-8 w-8 text-primary" />
            Agent Assistant
          </h1>
          <p className="text-muted-foreground mt-1">
            AI-powered agent for complex multi-step queries
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm ${isRunning ? 'bg-green-500/10 text-green-500' : 'bg-gray-500/10 text-gray-500'}`}>
            {isRunning ? '● Running' : '○ Idle'}
          </span>
        </div>
      </div>

      {/* Agent Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Query Input */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-500" />
            Agent Query
          </h2>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter a complex query for the agent to process..."
            className="w-full h-32 p-4 rounded-lg bg-background border border-border resize-none focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <div className="flex gap-3 mt-4">
            <button
              onClick={() => setIsRunning(!isRunning)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium ${
                isRunning 
                  ? 'bg-red-500 hover:bg-red-600 text-white' 
                  : 'bg-primary hover:bg-primary/90 text-primary-foreground'
              }`}
            >
              {isRunning ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              {isRunning ? 'Stop Agent' : 'Run Agent'}
            </button>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-accent">
              <RotateCcw className="h-4 w-4" />
              Reset
            </button>
          </div>
        </div>

        {/* Agent Config */}
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Agent Configuration
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-muted-foreground">Agent Type</label>
              <select className="w-full mt-1 p-2 rounded-lg bg-background border border-border">
                <option>ReAct Agent</option>
                <option>Chain-of-Thought</option>
                <option>Multi-Step Planner</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground">LLM Provider</label>
              <select className="w-full mt-1 p-2 rounded-lg bg-background border border-border">
                <option>GPT-4o</option>
                <option>Claude 3.5 Sonnet</option>
                <option>DeepSeek</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Max Steps</label>
              <input 
                type="number" 
                defaultValue={10}
                className="w-full mt-1 p-2 rounded-lg bg-background border border-border"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Agent Execution Log */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="font-semibold mb-4">Execution Log</h2>
        <div className="bg-background rounded-lg p-4 font-mono text-sm h-64 overflow-y-auto">
          <p className="text-muted-foreground">Agent execution log will appear here...</p>
        </div>
      </div>
    </div>
  );
}
