"use client";

import {
  FileText,
  MessageSquare,
  TrendingUp,
  Users,
  Clock,
  ArrowUpRight,
} from "lucide-react";
import { useAuth } from "../../contexts/auth-context";

const stats = [
  {
    name: "Total Documents",
    value: "2,847",
    change: "+12%",
    icon: FileText,
    color: "text-blue-500",
    bg: "bg-blue-500/10",
  },
  {
    name: "Queries Today",
    value: "1,429",
    change: "+23%",
    icon: MessageSquare,
    color: "text-green-500",
    bg: "bg-green-500/10",
  },
  {
    name: "Active Users",
    value: "342",
    change: "+8%",
    icon: Users,
    color: "text-purple-500",
    bg: "bg-purple-500/10",
  },
  {
    name: "Avg Response Time",
    value: "1.2s",
    change: "-15%",
    icon: Clock,
    color: "text-orange-500",
    bg: "bg-orange-500/10",
  },
];

const recentQueries = [
  {
    query: "What is the PTO policy for employees with 3+ years?",
    department: "HR",
    time: "2 min ago",
    status: "answered",
  },
  {
    query: "Contract termination clause requirements",
    department: "Legal",
    time: "5 min ago",
    status: "answered",
  },
  {
    query: "Q4 budget variance analysis",
    department: "Finance",
    time: "12 min ago",
    status: "processing",
  },
  {
    query: "HIPAA compliance requirements for patient data",
    department: "Clinical",
    time: "18 min ago",
    status: "answered",
  },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const firstName = user?.full_name?.split(" ")[0] || "User";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Welcome back, {firstName}! Here's your Huron Knowledge Assistant overview.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="p-6 rounded-xl border border-border bg-card hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`p-2 rounded-lg ${stat.bg}`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <span className="flex items-center text-sm text-green-500">
                <TrendingUp className="w-4 h-4 mr-1" />
                {stat.change}
              </span>
            </div>
            <h3 className="text-muted-foreground text-sm">{stat.name}</h3>
            <p className="text-2xl font-bold mt-1">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Queries */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-card">
          <div className="p-6 border-b border-border">
            <h2 className="font-semibold">Recent Queries</h2>
          </div>
          <div className="divide-y divide-border">
            {recentQueries.map((query, idx) => (
              <div key={idx} className="p-4 hover:bg-accent/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{query.query}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">
                        {query.department}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {query.time}
                      </span>
                    </div>
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded-full ${
                      query.status === "answered"
                        ? "bg-green-500/10 text-green-500"
                        : "bg-yellow-500/10 text-yellow-500"
                    }`}
                  >
                    {query.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div className="p-4 border-t border-border">
            <button className="text-sm text-primary hover:underline flex items-center">
              View all queries
              <ArrowUpRight className="w-4 h-4 ml-1" />
            </button>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="rounded-xl border border-border bg-card">
          <div className="p-6 border-b border-border">
            <h2 className="font-semibold">Quick Actions</h2>
          </div>
          <div className="p-4 space-y-3">
            <button className="w-full p-4 rounded-lg border border-border hover:bg-accent transition-colors text-left">
              <MessageSquare className="w-5 h-5 text-primary mb-2" />
              <p className="font-medium text-sm">Ask a Question</p>
              <p className="text-xs text-muted-foreground mt-1">
                Get instant answers from your knowledge base
              </p>
            </button>
            <button className="w-full p-4 rounded-lg border border-border hover:bg-accent transition-colors text-left">
              <FileText className="w-5 h-5 text-primary mb-2" />
              <p className="font-medium text-sm">Upload Document</p>
              <p className="text-xs text-muted-foreground mt-1">
                Add new documents to your department
              </p>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
