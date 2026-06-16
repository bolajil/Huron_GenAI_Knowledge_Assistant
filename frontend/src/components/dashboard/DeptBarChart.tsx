"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { Department } from "@/services/api";

const DEPT_COLORS: Record<string, string> = {
  hr:         "#10b981",
  finance:    "#3b82f6",
  legal:      "#6366f1",
  clinical:   "#ef4444",
  it:         "#8b5cf6",
  operations: "#f59e0b",
  marketing:  "#ec4899",
  company:    "#64748b",
  external:   "#94a3b8",
};

interface Props {
  departments: Department[];
}

export function DeptBarChart({ departments }: Props) {
  const data = departments
    .filter((d) => (d.query_count ?? 0) > 0)
    .sort((a, b) => (b.query_count ?? 0) - (a.query_count ?? 0))
    .slice(0, 7)
    .map((d) => ({
      name: d.display_name.length > 10 ? d.code.toUpperCase() : d.display_name,
      code: d.code,
      queries: d.query_count ?? 0,
    }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[180px] text-sm text-muted-foreground">
        No query data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <XAxis
          type="number"
          allowDecimals={false}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={56}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "hsl(235 30% 18%)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "8px",
            fontSize: 12,
          }}
          labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
          formatter={(v: number) => [v, "Queries"]}
        />
        <Bar dataKey="queries" radius={[0, 4, 4, 0]} maxBarSize={16}>
          {data.map((entry) => (
            <Cell key={entry.code} fill={DEPT_COLORS[entry.code] ?? "#64748b"} fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
