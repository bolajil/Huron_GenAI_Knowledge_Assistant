"use client";

import { Activity, Server, Database, Cpu, MemoryStick, Clock, CheckCircle, AlertTriangle } from "lucide-react";

const systemStatus = [
  { name: "API Server", status: "healthy", latency: "45ms", uptime: "99.9%" },
  { name: "Vector DB (FAISS)", status: "healthy", latency: "12ms", uptime: "100%" },
  { name: "Vector DB (Pinecone)", status: "healthy", latency: "89ms", uptime: "99.8%" },
  { name: "LLM Service (OpenAI)", status: "healthy", latency: "234ms", uptime: "99.7%" },
  { name: "Redis Cache", status: "warning", latency: "8ms", uptime: "98.5%" },
  { name: "Celery Workers", status: "healthy", latency: "N/A", uptime: "100%" },
];

export default function SystemMonitoringPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Activity className="h-8 w-8 text-green-500" />
          System Monitoring
        </h1>
        <p className="text-muted-foreground mt-1">
          Real-time system health and performance metrics
        </p>
      </div>

      {/* System Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between mb-2">
            <Cpu className="h-5 w-5 text-blue-500" />
            <span className="text-xs text-muted-foreground">CPU</span>
          </div>
          <p className="text-2xl font-bold">34%</p>
          <div className="w-full h-2 bg-muted rounded-full mt-2">
            <div className="h-full bg-blue-500 rounded-full" style={{ width: '34%' }}></div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between mb-2">
            <MemoryStick className="h-5 w-5 text-purple-500" />
            <span className="text-xs text-muted-foreground">Memory</span>
          </div>
          <p className="text-2xl font-bold">67%</p>
          <div className="w-full h-2 bg-muted rounded-full mt-2">
            <div className="h-full bg-purple-500 rounded-full" style={{ width: '67%' }}></div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between mb-2">
            <Database className="h-5 w-5 text-cyan-500" />
            <span className="text-xs text-muted-foreground">Storage</span>
          </div>
          <p className="text-2xl font-bold">45%</p>
          <div className="w-full h-2 bg-muted rounded-full mt-2">
            <div className="h-full bg-cyan-500 rounded-full" style={{ width: '45%' }}></div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between mb-2">
            <Clock className="h-5 w-5 text-orange-500" />
            <span className="text-xs text-muted-foreground">Avg Latency</span>
          </div>
          <p className="text-2xl font-bold">1.2s</p>
          <p className="text-xs text-green-500 mt-2">↓ 15% from yesterday</p>
        </div>
      </div>

      {/* Service Status */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="p-4 border-b border-border">
          <h2 className="font-semibold flex items-center gap-2">
            <Server className="h-5 w-5" />
            Service Status
          </h2>
        </div>
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-4 font-medium">Service</th>
              <th className="text-left p-4 font-medium">Status</th>
              <th className="text-left p-4 font-medium">Latency</th>
              <th className="text-left p-4 font-medium">Uptime</th>
            </tr>
          </thead>
          <tbody>
            {systemStatus.map((service) => (
              <tr key={service.name} className="border-t border-border">
                <td className="p-4 font-medium">{service.name}</td>
                <td className="p-4">
                  <span className={`flex items-center gap-2 ${
                    service.status === 'healthy' ? 'text-green-500' : 'text-yellow-500'
                  }`}>
                    {service.status === 'healthy' ? 
                      <CheckCircle className="h-4 w-4" /> : 
                      <AlertTriangle className="h-4 w-4" />
                    }
                    {service.status}
                  </span>
                </td>
                <td className="p-4">{service.latency}</td>
                <td className="p-4">{service.uptime}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Recent Alerts */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-yellow-500" />
          Recent Alerts
        </h2>
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
            <p className="text-sm font-medium text-yellow-500">Redis cache connection unstable</p>
            <p className="text-xs text-muted-foreground mt-1">2 minutes ago</p>
          </div>
          <div className="p-3 rounded-lg bg-muted">
            <p className="text-sm font-medium">OpenAI rate limit warning</p>
            <p className="text-xs text-muted-foreground mt-1">1 hour ago - Resolved</p>
          </div>
        </div>
      </div>
    </div>
  );
}
