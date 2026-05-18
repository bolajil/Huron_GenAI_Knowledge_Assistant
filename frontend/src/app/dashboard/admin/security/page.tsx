"use client";

import { Shield, Key, Lock, Fingerprint, AlertTriangle, CheckCircle } from "lucide-react";

export default function SecurityPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Shield className="h-8 w-8 text-red-500" />
          Security Settings
        </h1>
        <p className="text-muted-foreground mt-1">
          Configure authentication and security policies
        </p>
      </div>

      {/* Security Status */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: "SSL/TLS", status: true, icon: Lock },
          { label: "MFA Enabled", status: true, icon: Fingerprint },
          { label: "SSO Ready", status: true, icon: Key },
          { label: "Audit Logging", status: true, icon: Shield },
        ].map((item, idx) => (
          <div key={idx} className="p-4 rounded-xl border border-border bg-card">
            <div className="flex items-center justify-between">
              <item.icon className="h-6 w-6 text-muted-foreground" />
              {item.status ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
              )}
            </div>
            <p className="font-medium mt-2">{item.label}</p>
            <p className="text-sm text-muted-foreground">
              {item.status ? 'Active' : 'Configure'}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Password Policy */}
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Key className="h-5 w-5" />
            Password Policy
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-muted-foreground">Minimum Length</label>
              <input 
                type="number" 
                defaultValue={12}
                className="w-full mt-1 p-2 rounded-lg bg-background border border-border"
              />
            </div>
            <label className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 cursor-pointer">
              <span>Require uppercase</span>
              <input type="checkbox" defaultChecked className="w-5 h-5 rounded" />
            </label>
            <label className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 cursor-pointer">
              <span>Require numbers</span>
              <input type="checkbox" defaultChecked className="w-5 h-5 rounded" />
            </label>
            <label className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 cursor-pointer">
              <span>Require symbols</span>
              <input type="checkbox" defaultChecked className="w-5 h-5 rounded" />
            </label>
          </div>
        </div>

        {/* Session Settings */}
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Session Settings
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-muted-foreground">Session Timeout (minutes)</label>
              <input 
                type="number" 
                defaultValue={480}
                className="w-full mt-1 p-2 rounded-lg bg-background border border-border"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Max Login Attempts</label>
              <input 
                type="number" 
                defaultValue={5}
                className="w-full mt-1 p-2 rounded-lg bg-background border border-border"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Lockout Duration (minutes)</label>
              <input 
                type="number" 
                defaultValue={30}
                className="w-full mt-1 p-2 rounded-lg bg-background border border-border"
              />
            </div>
          </div>
        </div>
      </div>

      {/* MFA Settings */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Fingerprint className="h-5 w-5" />
          Multi-Factor Authentication
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <label className="flex items-center gap-3 p-4 rounded-lg border border-border cursor-pointer hover:bg-muted/50">
            <input type="checkbox" defaultChecked className="w-5 h-5 rounded" />
            <div>
              <p className="font-medium">TOTP Apps</p>
              <p className="text-sm text-muted-foreground">Google/Microsoft Authenticator</p>
            </div>
          </label>
          <label className="flex items-center gap-3 p-4 rounded-lg border border-border cursor-pointer hover:bg-muted/50">
            <input type="checkbox" className="w-5 h-5 rounded" />
            <div>
              <p className="font-medium">Email OTP</p>
              <p className="text-sm text-muted-foreground">Send code via email</p>
            </div>
          </label>
          <label className="flex items-center gap-3 p-4 rounded-lg border border-border cursor-pointer hover:bg-muted/50">
            <input type="checkbox" className="w-5 h-5 rounded" />
            <div>
              <p className="font-medium">SMS OTP</p>
              <p className="text-sm text-muted-foreground">Send code via SMS</p>
            </div>
          </label>
        </div>
      </div>
    </div>
  );
}
