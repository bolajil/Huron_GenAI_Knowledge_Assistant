"use client";

import { BarChart3, TrendingUp, Users, FileText, Clock, ArrowUpRight, ArrowDownRight } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-blue-500" />
          Analytics Dashboard
        </h1>
        <p className="text-muted-foreground mt-1">
          Usage metrics and performance analytics
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Queries", value: "14,829", change: "+23%", up: true, icon: FileText },
          { label: "Active Users", value: "342", change: "+8%", up: true, icon: Users },
          { label: "Avg Response Time", value: "1.2s", change: "-15%", up: true, icon: Clock },
          { label: "Success Rate", value: "94.2%", change: "+2.1%", up: true, icon: TrendingUp },
        ].map((metric, idx) => (
          <div key={idx} className="p-4 rounded-xl border border-border bg-card">
            <div className="flex items-center justify-between mb-2">
              <metric.icon className="h-5 w-5 text-muted-foreground" />
              <span className={`flex items-center text-sm ${metric.up ? 'text-green-500' : 'text-red-500'}`}>
                {metric.up ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                {metric.change}
              </span>
            </div>
            <p className="text-2xl font-bold">{metric.value}</p>
            <p className="text-sm text-muted-foreground">{metric.label}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4">Queries Over Time</h2>
          <div className="h-64 flex items-end justify-between gap-2">
            {[40, 65, 45, 80, 55, 90, 70, 85, 60, 95, 75, 88].map((height, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <div 
                  className="w-full bg-primary/80 rounded-t hover:bg-primary transition-colors"
                  style={{ height: `${height}%` }}
                ></div>
                <span className="text-xs text-muted-foreground">
                  {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][idx]}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4">Queries by Department</h2>
          <div className="space-y-4">
            {[
              { dept: "HR", queries: 3456, color: "bg-blue-500" },
              { dept: "Legal", queries: 2891, color: "bg-purple-500" },
              { dept: "Finance", queries: 2567, color: "bg-green-500" },
              { dept: "Clinical", queries: 2234, color: "bg-orange-500" },
              { dept: "Operations", queries: 1890, color: "bg-cyan-500" },
              { dept: "IT", queries: 1791, color: "bg-pink-500" },
            ].map((item) => (
              <div key={item.dept}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{item.dept}</span>
                  <span className="text-sm text-muted-foreground">{item.queries.toLocaleString()}</span>
                </div>
                <div className="w-full h-2 bg-muted rounded-full">
                  <div 
                    className={`h-full ${item.color} rounded-full`}
                    style={{ width: `${(item.queries / 3456) * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Queries */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="font-semibold mb-4">Top Queries This Week</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 font-medium">Query</th>
                <th className="text-left py-3 font-medium">Department</th>
                <th className="text-left py-3 font-medium">Count</th>
                <th className="text-left py-3 font-medium">Avg Time</th>
              </tr>
            </thead>
            <tbody>
              {[
                { query: "PTO policy details", dept: "HR", count: 234, time: "0.9s" },
                { query: "Contract templates", dept: "Legal", count: 189, time: "1.1s" },
                { query: "Budget approval process", dept: "Finance", count: 156, time: "1.3s" },
                { query: "HIPAA guidelines", dept: "Clinical", count: 143, time: "1.0s" },
                { query: "IT security policy", dept: "IT", count: 128, time: "0.8s" },
              ].map((row, idx) => (
                <tr key={idx} className="border-b border-border hover:bg-muted/50">
                  <td className="py-3">{row.query}</td>
                  <td className="py-3">
                    <span className="px-2 py-1 rounded text-xs bg-primary/10 text-primary">{row.dept}</span>
                  </td>
                  <td className="py-3">{row.count}</td>
                  <td className="py-3">{row.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
