"use client";

import { useState, useEffect } from "react";
import { Send, Mail, FileDown, BarChart2, Zap } from "lucide-react";
import { api } from "../../services/api";
import type { McpTool } from "../../services/api";
import ActionModal from "./ActionModal";

interface Props {
  resultText: string;
  query: string;
}

const TOOL_ICONS: Record<string, React.ReactNode> = {
  slack:         <Send className="h-3.5 w-3.5" />,
  email:         <Mail className="h-3.5 w-3.5" />,
  pdf_report:    <FileDown className="h-3.5 w-3.5" />,
  data_analyzer: <BarChart2 className="h-3.5 w-3.5" />,
};

export default function ActionBar({ resultText, query }: Props) {
  const [tools, setTools]         = useState<McpTool[]>([]);
  const [activeTool, setActiveTool] = useState<McpTool | null>(null);

  useEffect(() => {
    api.listMcpTools()
      .then(({ tools }) => setTools(tools))
      .catch(() => {});
  }, []);

  if (tools.length === 0) return null;

  return (
    <>
      <div className="pt-4 border-t border-border">
        <div className="flex items-center gap-1.5 mb-2">
          <Zap className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs text-muted-foreground font-medium">Actions</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {tools.map((tool) => (
            <button
              key={tool.id}
              onClick={() => setActiveTool(tool)}
              title={tool.description}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-border bg-muted/40 hover:bg-accent transition-colors text-foreground/80 hover:text-foreground"
            >
              {TOOL_ICONS[tool.tool_type] ?? <Zap className="h-3.5 w-3.5" />}
              {tool.name}
              {!tool.configured &&
                tool.tool_type !== "pdf_report" &&
                tool.tool_type !== "data_analyzer" && (
                  <span className="text-[10px] text-amber-500">(needs setup)</span>
                )}
            </button>
          ))}
        </div>
      </div>

      {activeTool && (
        <ActionModal
          tool={activeTool}
          resultText={resultText}
          query={query}
          onClose={() => setActiveTool(null)}
        />
      )}
    </>
  );
}
