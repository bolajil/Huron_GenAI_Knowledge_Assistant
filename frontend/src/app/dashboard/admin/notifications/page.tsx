"use client";

import { Bell, Mail, MessageSquare, Smartphone, Settings } from "lucide-react";

export default function NotificationsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Bell className="h-8 w-8 text-yellow-500" />
          Notification Settings
        </h1>
        <p className="text-muted-foreground mt-1">
          Configure system alerts and notifications
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Email Notifications
          </h2>
          <div className="space-y-4">
            {[
              { label: "System alerts", enabled: true },
              { label: "Daily digest", enabled: true },
              { label: "Query failures", enabled: false },
              { label: "New user registrations", enabled: true },
            ].map((item, idx) => (
              <label key={idx} className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 cursor-pointer">
                <span>{item.label}</span>
                <input type="checkbox" defaultChecked={item.enabled} className="w-5 h-5 rounded" />
              </label>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Slack/Teams Integration
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-muted-foreground">Webhook URL</label>
              <input 
                type="url"
                placeholder="https://hooks.slack.com/services/..."
                className="w-full mt-1 p-2 rounded-lg bg-background border border-border"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Channel</label>
              <input 
                type="text"
                placeholder="#alerts"
                className="w-full mt-1 p-2 rounded-lg bg-background border border-border"
              />
            </div>
            <button className="px-4 py-2 bg-primary text-primary-foreground rounded-lg">
              Test Connection
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
