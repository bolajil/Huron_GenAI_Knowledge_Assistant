# Huron GenAI v3 — RBAC Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade all 8 files to v3 — adding 4-tier RBAC (root → dept_admin → power_user → user/viewer), real logout with JWT blacklist, live dashboard stats, access request workflow, and separation of duty matching Pinecone namespaces — without breaking the login/MFA pages or any existing dashboard sub-pages.

**Architecture:** Backend `main.py` is a full replacement that introduces new DB tables (departments, access_requests, audit_log, query_log, token_blacklist) alongside the upgraded users table. Frontend files receive cascading updates: `api.ts` gains new methods, `auth-context.tsx` adds `isRoot()`/`isDeptAdmin()` and async logout, then dashboard/admin/sidebar/header consume those additions. New file `access-requests/page.tsx` is created.

**Tech Stack:** FastAPI, SQLite, bcrypt, PyJWT 2.8, Next.js 14 App Router, TypeScript, Tailwind CSS, lucide-react

---

## Pre-flight check

**Do NOT touch these files — they are working and out of scope:**
- `frontend/src/components/Auth/Login.tsx`
- `frontend/src/components/ui/login-form.tsx`
- `frontend/src/app/globals.css`
- All pages under `dashboard/` except `dashboard/page.tsx` and `dashboard/admin/page.tsx`

**Known risk — MFA field name mismatch:** The current `mfa/page.tsx` sends `session_token`; v3 backend expects `pending_token`. Task 2 fixes this before the backend is replaced.

---

## File Map

| # | File | Action | Notes |
|---|------|---------|-------|
| 1 | `backend/main.py` | Replace | New DB schema + all v3 routes |
| 2 | `frontend/src/app/mfa/page.tsx` | Patch | `session_token` → `pending_token` |
| 3 | `frontend/src/services/api.ts` | Replace | Add 8 new typed methods |
| 4 | `frontend/src/contexts/auth-context.tsx` | Replace | New roles, async logout, `isRoot()`, `isDeptAdmin()` |
| 5 | `frontend/src/app/dashboard/page.tsx` | Replace | Real API data, 30 s refresh |
| 6 | `frontend/src/app/dashboard/admin/page.tsx` | Replace | Full RBAC admin UI |
| 7 | `frontend/src/app/dashboard/admin/access-requests/page.tsx` | Create | New access-request workflow page |
| 8 | `frontend/src/components/sidebar.tsx` | Replace | RBAC-filtered nav, role badge |
| 9 | `frontend/src/components/header.tsx` | Replace | Async logout, namespace display |

---

## Task 1 — Replace backend/main.py (v3 RBAC backend)

**Files:**
- Modify: `backend/main.py`

> Run the backend first and verify health before touching any frontend file.

- [ ] **Step 1.1 — Kill any running uvicorn process**

```bash
# In PowerShell/terminal — find and kill the port 8000 process
npx kill-port 8000 2>/dev/null || true
```

- [ ] **Step 1.2 — Back up current main.py**

```bash
cp backend/main.py backend/main.py.v2.bak
```

- [ ] **Step 1.3 — Write the new backend/main.py**

Replace the entire file with the v3 source provided in the spec. The critical sections are:

**Imports block (top of file):**
```python
"""
Huron GenAI Knowledge Assistant - FastAPI Backend v3
4-tier RBAC, JWT blacklist, separation of duty, access requests, audit log
"""
from __future__ import annotations
import os, sys, sqlite3, logging, secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import bcrypt, jwt, uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))
logger = logging.getLogger(__name__)
```

**Key constants:**
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production-use-strong-random-key")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8
DB_PATH = Path(__file__).parent.parent / "data" / "huron.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_token_blacklist: set[str] = set()
```

**Role hierarchy (copy exactly):**
```python
ROLE_CLEARANCE = {"root": 5, "dept_admin": 4, "power_user": 3, "user": 2, "viewer": 1}

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "root": [
        "query","chat","ingest","research","agent","admin","manage_users",
        "manage_departments","manage_all_depts","create_dept_admin",
        "approve_requests","view_audit_log","mcp","analytics",
    ],
    "dept_admin": [
        "query","chat","ingest","research","agent","manage_users",
        "manage_dept_users","approve_requests","analytics","mcp",
    ],
    "power_user": ["query","chat","ingest","research","agent","analytics"],
    "user":       ["query","chat","ingest"],
    "viewer":     ["query","chat"],
}
```

**Seed root user credentials (important for first login):**
- username: `root`
- password: `HuronRoot2026!`
- role: `root`
- department: `all`

**CORS origins must include `localhost:3000`:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000","http://localhost:3001",
        "http://127.0.0.1:3000","http://127.0.0.1:3001",
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
```

**MFA endpoint — expects `pending_token` field (not `session_token`):**
```python
@app.post("/api/v1/auth/mfa/verify")
async def mfa_verify(body: dict):
    code = body.get("code", "")
    if len(code) == 6 and code.isdigit():
        pending_token = body.get("pending_token")
        if pending_token:
            payload = verify_token(pending_token)
            if payload:
                return {"status": "success", "access_token": pending_token, "token_type": "bearer"}
        else:
            # Dev fallback: accept any 6-digit code without a pending token
            return {
                "status": "success",
                "access_token": "dev-bypass",
                "token_type": "bearer",
                "message": "MFA verified (dev mode)",
            }
    raise HTTPException(status_code=400, detail="Invalid MFA code")
```

> **Note:** The full v3 file is 1272 lines. Copy the complete file from the spec. All routes listed in the architecture doc must be present.

- [ ] **Step 1.4 — Start the backend and verify health**

```bash
cd backend
uvicorn main:app --reload --port 8000
```

In a separate terminal:
```bash
curl -s http://localhost:8000/health | python -m json.tool
# Expected: {"status": "healthy", ...}
```

- [ ] **Step 1.5 — Verify login works with root credentials**

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"HuronRoot2026!"}' | python -m json.tool
# Expected: {"access_token": "...", "user": {"role": "root", ...}}
```

- [ ] **Step 1.6 — Verify MFA still works**

```bash
# First get a token from login, then:
curl -s -X POST http://localhost:8000/api/v1/auth/mfa/verify \
  -H "Content-Type: application/json" \
  -d '{"code":"123456"}' | python -m json.tool
# Expected: {"status": "success", "access_token": "dev-bypass", ...}
```

- [ ] **Step 1.7 — Commit**

```bash
git add backend/main.py
git commit -m "feat(backend): v3 RBAC — 4-tier hierarchy, token blacklist, access requests, audit log"
```

---

## Task 2 — Fix MFA page field name

**Files:**
- Modify: `frontend/src/app/mfa/page.tsx` (line ~80)

The v3 backend reads `body.get("pending_token")` not `body.get("session_token")`.

- [ ] **Step 2.1 — Update the fetch body in handleVerify**

Find this line in `mfa/page.tsx`:
```tsx
body: JSON.stringify({ code, session_token: pendingToken }),
```

Replace with:
```tsx
body: JSON.stringify({ code, pending_token: pendingToken }),
```

- [ ] **Step 2.2 — Verify MFA flow in browser**

Navigate to `http://localhost:3000`, log in as `admin` / `admin123` (or `root` / `HuronRoot2026!`), enter any 6-digit code — should reach dashboard.

- [ ] **Step 2.3 — Commit**

```bash
git add frontend/src/app/mfa/page.tsx
git commit -m "fix(mfa): send pending_token field matching v3 backend expectation"
```

---

## Task 3 — Replace api.ts (expanded typed client)

**Files:**
- Modify: `frontend/src/services/api.ts`

Replace the entire file with the v3 version. Key additions over v2:

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────

export type UserRole = "root" | "dept_admin" | "power_user" | "user" | "viewer";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  department: string;
  role: UserRole;
  permissions: string[];
  clearance_level?: number;
}

export interface StatsResponse {
  total_documents: number;
  queries_today: number;
  active_users: number;
  avg_response_time: number;
  avg_faithfulness: number;
  pinecone: { status: string; index?: string; error?: string };
  scope: string;
}

export interface RecentQuery {
  id: number;
  query_text: string;
  dept_code: string;
  response_ms: number;
  faithfulness: number;
  created_at: string;
  username?: string;
}

export interface AccessRequest {
  id: number;
  requester_id: number;
  dept_code: string;
  requested_tab: string;
  requested_role: string;
  justification: string;
  status: "pending" | "approved" | "rejected";
  requester_name: string;
  requester_email: string;
  reviewer_name?: string;
  reviewed_at?: string;
  created_at: string;
}

export interface Department {
  id: number;
  code: string;
  display_name: string;
  namespace: string;
  classification: string;
  is_active: number;
  admin_username?: string;
  doc_count: number;
  query_count: number;
  user_count: number;
}

// ── Auth header helper ─────────────────────────────────────────────────────

const authHeader = (): HeadersInit => {
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
};

// ── API client ─────────────────────────────────────────────────────────────

export const api = {
  // Auth
  async login(username: string, password: string, auth_method = "local") {
    const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, auth_method }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Login failed"); }
    return res.json();
  },

  async logout() {
    const token = localStorage.getItem("auth_token");
    if (!token) return;
    try {
      await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch { /* fire-and-forget */ }
  },

  async validateToken(): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/validate`, { headers: authHeader() });
      return res.ok;
    } catch { return false; }
  },

  // Dashboard stats
  async getStats(): Promise<StatsResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/admin/stats`, { headers: authHeader() });
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
  },

  async getRecentQueries(limit = 20): Promise<{ queries: RecentQuery[] }> {
    const res = await fetch(`${API_BASE_URL}/api/v1/admin/stats/recent-queries?limit=${limit}`, { headers: authHeader() });
    if (!res.ok) throw new Error("Failed to fetch recent queries");
    return res.json();
  },

  // Root-only user management
  async rootListAllUsers(): Promise<{ users: User[] }> {
    const res = await fetch(`${API_BASE_URL}/api/v1/root/users`, { headers: authHeader() });
    if (!res.ok) throw new Error("Failed to fetch users");
    return res.json();
  },

  async rootCreateUser(data: { username: string; email: string; full_name: string; password: string; role: string; department: string }) {
    const res = await fetch(`${API_BASE_URL}/api/v1/root/users`, {
      method: "POST", headers: authHeader(), body: JSON.stringify(data),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Create failed"); }
    return res.json();
  },

  async rootUpdateUser(userId: number, data: Partial<{ full_name: string; role: string; department: string; is_active: boolean }>) {
    const res = await fetch(`${API_BASE_URL}/api/v1/root/users/${userId}`, {
      method: "PUT", headers: authHeader(), body: JSON.stringify(data),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Update failed"); }
    return res.json();
  },

  async rootDeleteUser(userId: number) {
    const res = await fetch(`${API_BASE_URL}/api/v1/root/users/${userId}`, {
      method: "DELETE", headers: authHeader(),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Delete failed"); }
    return res.json();
  },

  async rootListDepartments(): Promise<{ departments: Department[] }> {
    const res = await fetch(`${API_BASE_URL}/api/v1/root/departments`, { headers: authHeader() });
    if (!res.ok) throw new Error("Failed to fetch departments");
    return res.json();
  },

  // Dept admin user management
  async deptListUsers(): Promise<{ users: User[] }> {
    const res = await fetch(`${API_BASE_URL}/api/v1/admin/dept-users`, { headers: authHeader() });
    if (!res.ok) throw new Error("Failed to fetch dept users");
    return res.json();
  },

  async deptCreateUser(data: { username: string; email: string; full_name: string; password: string; role: string; department: string }) {
    const res = await fetch(`${API_BASE_URL}/api/v1/admin/dept-users`, {
      method: "POST", headers: authHeader(), body: JSON.stringify(data),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Create failed"); }
    return res.json();
  },

  // Access requests
  async listRequestableTabs() {
    const res = await fetch(`${API_BASE_URL}/api/v1/access-requests/tabs`, { headers: authHeader() });
    if (!res.ok) throw new Error("Failed to fetch tabs");
    return res.json();
  },

  async submitAccessRequest(data: { dept_code: string; requested_tab: string; requested_role: string; justification: string }) {
    const res = await fetch(`${API_BASE_URL}/api/v1/access-requests`, {
      method: "POST", headers: authHeader(), body: JSON.stringify(data),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Submit failed"); }
    return res.json();
  },

  async listAccessRequests(status_filter?: string): Promise<{ requests: AccessRequest[] }> {
    const url = status_filter
      ? `${API_BASE_URL}/api/v1/access-requests?status_filter=${status_filter}`
      : `${API_BASE_URL}/api/v1/access-requests`;
    const res = await fetch(url, { headers: authHeader() });
    if (!res.ok) throw new Error("Failed to fetch requests");
    return res.json();
  },

  async reviewAccessRequest(request_id: number, action: "approve" | "reject", note?: string) {
    const res = await fetch(`${API_BASE_URL}/api/v1/access-requests/review`, {
      method: "POST", headers: authHeader(),
      body: JSON.stringify({ request_id, action, note }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Review failed"); }
    return res.json();
  },

  // Compat aliases used by existing pages
  async getUsers(): Promise<{ users: User[] }> {
    const res = await fetch(`${API_BASE_URL}/api/v1/admin/users`, { headers: authHeader() });
    if (!res.ok) throw new Error("Failed to fetch users");
    return res.json();
  },

  async healthCheck() {
    return fetch(`${API_BASE_URL}/health`).then((r) => r.json());
  },

  // Query / Chat / Ingest (unchanged signatures)
  async query(queryText: string, department = "general", top_k = 10) {
    const res = await fetch(`${API_BASE_URL}/api/v1/query`, {
      method: "POST", headers: authHeader(),
      body: JSON.stringify({ query: queryText, department, top_k }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Query failed"); }
    return res.json();
  },

  async chat(messages: Array<{ role: string; content: string }>, department = "general") {
    const res = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: "POST", headers: authHeader(),
      body: JSON.stringify({ messages, department }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Chat failed"); }
    return res.json();
  },

  async ingestDocument(file: File, department = "general", sensitivity_level = "internal") {
    const form = new FormData();
    form.append("file", file);
    form.append("department", department);
    form.append("sensitivity_level", sensitivity_level);
    const token = localStorage.getItem("auth_token");
    const res = await fetch(`${API_BASE_URL}/api/v1/ingest`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Upload failed"); }
    return res.json();
  },
};

export default api;
```

- [ ] **Step 3.1 — Write the complete api.ts file above**

- [ ] **Step 3.2 — Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
# Expected: no errors related to api.ts
```

- [ ] **Step 3.3 — Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): v3 typed client — RBAC methods, stats, access requests, departments"
```

---

## Task 4 — Replace auth-context.tsx

**Files:**
- Modify: `frontend/src/contexts/auth-context.tsx`

Key changes vs current:
- `User.role` type gains `"root"` and `"dept_admin"`
- `logout()` becomes `async` and calls `api.logout()` before clearing localStorage
- New helpers: `isRoot()`, `isDeptAdmin()`, `hasPermission()` updated to handle `root` role
- Existing `hasRole()` kept for backward compat

```tsx
"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, User } from "../services/api";

export type { User };

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => Promise<void>;
  isRoot: () => boolean;
  isDeptAdmin: () => boolean;
  hasPermission: (permission: string) => boolean;
  hasRole: (roles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem("auth_token");
        const savedUser = localStorage.getItem("user");
        if (token && savedUser) {
          const valid = await api.validateToken();
          if (valid) {
            setUser(JSON.parse(savedUser));
          } else {
            localStorage.removeItem("auth_token");
            localStorage.removeItem("user");
          }
        }
      } catch {
        const savedUser = localStorage.getItem("user");
        if (savedUser) setUser(JSON.parse(savedUser));
      } finally {
        setIsLoading(false);
      }
    };
    checkAuth();
  }, []);

  const login = (token: string, userData: User) => {
    localStorage.setItem("auth_token", token);
    localStorage.setItem("user", JSON.stringify(userData));
    setUser(userData);
  };

  const logout = async () => {
    await api.logout();           // blacklist token on server
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user");
    localStorage.removeItem("mfa_verified");
    setUser(null);
    router.push("/");
  };

  const isRoot = () => user?.role === "root";
  const isDeptAdmin = () => user?.role === "dept_admin" || user?.role === "root";

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    if (user.role === "root") return true;
    return user.permissions?.includes(permission) ?? false;
  };

  const hasRole = (roles: string[]): boolean => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider value={{
      user, isLoading, isAuthenticated: !!user,
      login, logout, isRoot, isDeptAdmin, hasPermission, hasRole,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
```

- [ ] **Step 4.1 — Write the complete auth-context.tsx above**

- [ ] **Step 4.2 — Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4.3 — Commit**

```bash
git add frontend/src/contexts/auth-context.tsx
git commit -m "feat(auth): v3 context — root/dept_admin roles, async logout with blacklist, isRoot/isDeptAdmin helpers"
```

---

## Task 5 — Replace dashboard/page.tsx (live stats + real queries)

**Files:**
- Modify: `frontend/src/app/dashboard/page.tsx`

Replace hardcoded arrays with `api.getStats()` and `api.getRecentQueries()`. Auto-refresh every 30 s.

```tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import { FileText, MessageSquare, TrendingUp, Users, Clock, ArrowUpRight, AlertCircle, RefreshCw } from "lucide-react";
import { useAuth } from "../../contexts/auth-context";
import { api, StatsResponse, RecentQuery } from "../../services/api";

export default function DashboardPage() {
  const { user, hasPermission } = useAuth();
  const firstName = user?.full_name?.split(" ")[0] || "User";

  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [queries, setQueries] = useState<RecentQuery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const fetchData = useCallback(async () => {
    try {
      const [s, q] = await Promise.all([
        api.getStats(),
        api.getRecentQueries(10),
      ]);
      setStats(s);
      setQueries(q.queries);
      setError("");
      setLastRefresh(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const statCards = stats
    ? [
        { name: "Total Documents", value: stats.total_documents.toLocaleString(), icon: FileText, color: "text-blue-500", bg: "bg-blue-500/10" },
        { name: "Queries Today", value: stats.queries_today.toLocaleString(), icon: MessageSquare, color: "text-green-500", bg: "bg-green-500/10" },
        { name: "Active Users", value: stats.active_users.toLocaleString(), icon: Users, color: "text-purple-500", bg: "bg-purple-500/10" },
        { name: "Avg Response", value: `${stats.avg_response_time}s`, icon: Clock, color: "text-orange-500", bg: "bg-orange-500/10" },
      ]
    : [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Welcome back, {firstName}!{" "}
            {stats && (
              <span className="text-xs ml-2 text-muted-foreground">
                Scope: <span className="font-medium">{stats.scope}</span>
                {stats.pinecone.status === "connected" && (
                  <span className="ml-2 text-green-500">● Pinecone connected</span>
                )}
              </span>
            )}
          </p>
        </div>
        <button
          onClick={() => { setLoading(true); fetchData(); }}
          className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-border hover:bg-accent transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive border border-destructive/20">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {loading && !stats
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="p-6 rounded-xl border border-border bg-card animate-pulse h-28" />
            ))
          : statCards.map((stat) => (
              <div key={stat.name} className="p-6 rounded-xl border border-border bg-card hover:shadow-lg transition-shadow">
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-2 rounded-lg ${stat.bg}`}>
                    <stat.icon className={`w-5 h-5 ${stat.color}`} />
                  </div>
                  <span className="flex items-center text-sm text-green-500">
                    <TrendingUp className="w-4 h-4 mr-1" />
                    live
                  </span>
                </div>
                <h3 className="text-muted-foreground text-sm">{stat.name}</h3>
                <p className="text-2xl font-bold mt-1">{stat.value}</p>
              </div>
            ))}
      </div>

      {/* Recent Queries */}
      <div className="rounded-xl border border-border bg-card">
        <div className="p-6 border-b border-border flex items-center justify-between">
          <h2 className="font-semibold">Recent Queries</h2>
          <span className="text-xs text-muted-foreground">
            Last refreshed {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
        <div className="divide-y divide-border">
          {queries.length === 0 && !loading ? (
            <div className="p-8 text-center text-muted-foreground text-sm">No queries yet in this scope.</div>
          ) : (
            queries.map((q) => (
              <div key={q.id} className="p-4 hover:bg-accent/50 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{q.query_text}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                        {q.dept_code}
                      </span>
                      {q.username && (
                        <span className="text-xs text-muted-foreground">@{q.username}</span>
                      )}
                      <span className="text-xs text-muted-foreground">{q.response_ms}ms</span>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(q.created_at).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
        <div className="p-4 border-t border-border">
          <button className="text-sm text-primary hover:underline flex items-center">
            View all queries <ArrowUpRight className="w-4 h-4 ml-1" />
          </button>
        </div>
      </div>

      {/* Pinecone status (root only) */}
      {stats && hasPermission("view_audit_log") && (
        <div className={`p-4 rounded-lg border text-sm ${
          stats.pinecone.status === "connected"
            ? "border-green-500/30 bg-green-500/5 text-green-400"
            : "border-yellow-500/30 bg-yellow-500/5 text-yellow-400"
        }`}>
          <strong>Pinecone:</strong>{" "}
          {stats.pinecone.status === "connected"
            ? `Connected — index: ${stats.pinecone.index}`
            : `Unavailable — ${stats.pinecone.error}`}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5.1 — Write the complete dashboard/page.tsx above**

- [ ] **Step 5.2 — Load dashboard in browser and verify live stats appear**

Expected: stat cards show real values from DB (may be zeros on fresh DB), no hardcoded "2,847" or "1,429".

- [ ] **Step 5.3 — Commit**

```bash
git add frontend/src/app/dashboard/page.tsx
git commit -m "feat(dashboard): live stats from API with 30s auto-refresh and Pinecone status"
```

---

## Task 6 — Replace admin/page.tsx (RBAC-aware admin UI)

**Files:**
- Modify: `frontend/src/app/dashboard/admin/page.tsx`

This replaces the thin `<AdminPanel />` wrapper with a full RBAC-aware UI. Root users see all users across all departments; dept_admin sees only their own department.

```tsx
"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../../../contexts/auth-context";
import { api, User } from "../../../services/api";
import { Users, UserPlus, Shield, Trash2, AlertCircle, CheckCircle, RefreshCw, Building2 } from "lucide-react";

const ROLES = ["viewer", "user", "power_user", "dept_admin"] as const;
const DEPARTMENTS = ["hr", "legal", "finance", "clinical", "operations", "it", "marketing", "external"];

interface NewUserForm {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: string;
  department: string;
}

const emptyForm: NewUserForm = {
  username: "", email: "", full_name: "", password: "", role: "user", department: "hr",
};

export default function AdminPage() {
  const { user, isRoot, isDeptAdmin } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NewUserForm>(emptyForm);
  const [submitting, setSubmitting] = useState(false);

  if (!isDeptAdmin()) {
    return (
      <div className="flex items-center gap-3 p-6 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive">
        <Shield className="w-5 h-5 shrink-0" />
        <span>Admin access required. Request access via the Access Requests page.</span>
      </div>
    );
  }

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = isRoot()
        ? await api.rootListAllUsers()
        : await api.deptListUsers();
      setUsers(res.users);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(""); setSuccess("");
    try {
      if (isRoot()) {
        await api.rootCreateUser(form);
      } else {
        await api.deptCreateUser({ ...form, department: user!.department });
      }
      setSuccess(`User ${form.username} created successfully`);
      setForm(emptyForm);
      setShowForm(false);
      fetchUsers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeactivate = async (userId: number, username: string) => {
    if (!confirm(`Deactivate user ${username}?`)) return;
    try {
      await api.rootUpdateUser(userId, { is_active: false });
      setSuccess(`User ${username} deactivated`);
      fetchUsers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Deactivate failed");
    }
  };

  const roleBadge = (role: string) => {
    const colors: Record<string, string> = {
      root: "bg-red-500/15 text-red-400 border-red-500/30",
      dept_admin: "bg-purple-500/15 text-purple-400 border-purple-500/30",
      power_user: "bg-blue-500/15 text-blue-400 border-blue-500/30",
      user: "bg-green-500/15 text-green-400 border-green-500/30",
      viewer: "bg-gray-500/15 text-gray-400 border-gray-500/30",
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full border ${colors[role] || colors.user}`}>
        {role}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">User Administration</h1>
          <p className="text-muted-foreground mt-1">
            {isRoot() ? "All departments — root view" : `Department: ${user?.department}`}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchUsers} className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-border hover:bg-accent">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium"
          >
            <UserPlus className="w-4 h-4" />
            Add User
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-green-500/10 text-green-400 border border-green-500/20 text-sm">
          <CheckCircle className="w-4 h-4 shrink-0" /> {success}
        </div>
      )}

      {/* Create user form */}
      {showForm && (
        <form onSubmit={handleCreate} className="rounded-xl border border-border bg-card p-6 space-y-4">
          <h2 className="font-semibold flex items-center gap-2"><UserPlus className="w-4 h-4" /> New User</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(["username", "email", "full_name", "password"] as const).map((field) => (
              <div key={field}>
                <label className="block text-sm font-medium mb-1 capitalize">{field.replace("_", " ")}</label>
                <input
                  type={field === "password" ? "password" : field === "email" ? "email" : "text"}
                  value={form[field]}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                  required
                  className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            ))}
            <div>
              <label className="block text-sm font-medium mb-1">Role</label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {(isRoot() ? [...ROLES, "dept_admin"] : ROLES).map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            {isRoot() && (
              <div>
                <label className="block text-sm font-medium mb-1">Department</label>
                <select
                  value={form.department}
                  onChange={(e) => setForm({ ...form, department: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
            )}
          </div>
          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={submitting}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              {submitting ? "Creating..." : "Create User"}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-accent">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Users table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="p-4 border-b border-border flex items-center gap-2">
          <Users className="w-4 h-4" />
          <span className="font-medium">{users.length} Users</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">User</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Role</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Department</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                {isRoot() && <th className="text-right px-4 py-3 font-medium text-muted-foreground">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading
                ? Array.from({ length: 3 }).map((_, i) => (
                    <tr key={i}><td colSpan={5} className="px-4 py-3"><div className="h-4 bg-muted animate-pulse rounded w-full" /></td></tr>
                  ))
                : users.map((u) => (
                    <tr key={u.id} className="hover:bg-accent/30 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium">{u.full_name || u.username}</div>
                        <div className="text-xs text-muted-foreground">{u.email}</div>
                      </td>
                      <td className="px-4 py-3">{roleBadge(u.role)}</td>
                      <td className="px-4 py-3">
                        <span className="flex items-center gap-1"><Building2 className="w-3 h-3" />{u.department}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${(u as any).is_active !== 0 ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-400"}`}>
                          {(u as any).is_active !== 0 ? "active" : "inactive"}
                        </span>
                      </td>
                      {isRoot() && (
                        <td className="px-4 py-3 text-right">
                          {u.role !== "root" && (
                            <button onClick={() => handleDeactivate(parseInt(u.id), u.username)}
                              className="p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                              title="Deactivate">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6.1 — Write the complete admin/page.tsx above**

- [ ] **Step 6.2 — Verify admin page loads for root user**

Log in as `root` / `HuronRoot2026!` → navigate to `/dashboard/admin`. Expect user table with root user visible.

- [ ] **Step 6.3 — Commit**

```bash
git add frontend/src/app/dashboard/admin/page.tsx
git commit -m "feat(admin): v3 RBAC user management — root sees all, dept_admin sees own dept"
```

---

## Task 7 — Create access-requests/page.tsx (new page)

**Files:**
- Create: `frontend/src/app/dashboard/admin/access-requests/page.tsx`

```tsx
"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../../../../contexts/auth-context";
import { api, AccessRequest } from "../../../../services/api";
import { ClipboardList, CheckCircle, XCircle, Clock, AlertCircle, Send } from "lucide-react";

type TabFilter = "all" | "pending" | "approved" | "rejected";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
  approved: "bg-green-500/10 text-green-400 border-green-500/30",
  rejected: "bg-red-500/10 text-red-400 border-red-500/30",
};

export default function AccessRequestsPage() {
  const { user, isDeptAdmin } = useAuth();
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [tabs, setTabs] = useState<{ tab: string; label: string; currently_accessible: boolean }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [activeFilter, setActiveFilter] = useState<TabFilter>("all");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ dept_code: user?.department || "hr", requested_tab: "query", requested_role: "user", justification: "" });
  const [submitting, setSubmitting] = useState(false);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [reqRes, tabRes] = await Promise.all([
        api.listAccessRequests(activeFilter === "all" ? undefined : activeFilter),
        api.listRequestableTabs(),
      ]);
      setRequests(reqRes.requests);
      setTabs(tabRes.tabs);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, [activeFilter]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.justification.trim()) { setError("Justification is required"); return; }
    setSubmitting(true); setError(""); setSuccess("");
    try {
      await api.submitAccessRequest(form);
      setSuccess("Access request submitted successfully. A dept admin will review it.");
      setShowForm(false);
      setForm({ ...form, justification: "" });
      fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReview = async (id: number, action: "approve" | "reject") => {
    try {
      await api.reviewAccessRequest(id, action);
      setSuccess(`Request ${action}d`);
      fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed");
    }
  };

  const filterCounts = {
    all: requests.length,
    pending: requests.filter((r) => r.status === "pending").length,
    approved: requests.filter((r) => r.status === "approved").length,
    rejected: requests.filter((r) => r.status === "rejected").length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Access Requests</h1>
          <p className="text-muted-foreground mt-1">Request additional permissions or review pending requests</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium"
        >
          <Send className="w-4 h-4" />
          New Request
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-green-500/10 text-green-400 border border-green-500/20 text-sm">
          <CheckCircle className="w-4 h-4 shrink-0" /> {success}
        </div>
      )}

      {/* New request form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="rounded-xl border border-border bg-card p-6 space-y-4">
          <h2 className="font-semibold flex items-center gap-2"><ClipboardList className="w-4 h-4" /> New Access Request</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Tab / Feature</label>
              <select value={form.requested_tab} onChange={(e) => setForm({ ...form, requested_tab: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring">
                {tabs.map((t) => (
                  <option key={t.tab} value={t.tab} disabled={t.currently_accessible}>
                    {t.label}{t.currently_accessible ? " (already accessible)" : ""}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Requested Role</label>
              <select value={form.requested_role} onChange={(e) => setForm({ ...form, requested_role: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring">
                {["viewer", "user", "power_user"].map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Business Justification <span className="text-destructive">*</span></label>
            <textarea value={form.justification} onChange={(e) => setForm({ ...form, justification: e.target.value })}
              rows={3} required placeholder="Explain why you need this access..."
              className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
          </div>
          <div className="flex gap-3">
            <button type="submit" disabled={submitting}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              {submitting ? "Submitting..." : "Submit Request"}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-accent">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Filter tabs */}
      <div className="flex gap-1 bg-muted/30 rounded-xl p-1 w-fit">
        {(["all", "pending", "approved", "rejected"] as TabFilter[]).map((f) => (
          <button key={f} onClick={() => setActiveFilter(f)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all capitalize ${
              activeFilter === f ? "bg-card shadow text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}>
            {f} ({filterCounts[f]})
          </button>
        ))}
      </div>

      {/* Requests list */}
      <div className="space-y-3">
        {loading
          ? Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-20 rounded-xl border border-border bg-card animate-pulse" />
            ))
          : requests.length === 0
          ? (
              <div className="text-center py-12 text-muted-foreground">
                <ClipboardList className="w-8 h-8 mx-auto mb-3 opacity-40" />
                <p>No {activeFilter === "all" ? "" : activeFilter} access requests.</p>
              </div>
            )
          : requests.map((req) => (
              <div key={req.id} className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm">{req.requester_name}</span>
                      <span className="text-muted-foreground text-xs">→</span>
                      <span className="text-sm font-medium text-primary">{req.requested_tab}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_STYLES[req.status]}`}>
                        {req.status}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">{req.justification}</p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>Dept: {req.dept_code}</span>
                      <span>Role: {req.requested_role}</span>
                      <span>{new Date(req.created_at).toLocaleDateString()}</span>
                      {req.reviewer_name && <span>Reviewed by: {req.reviewer_name}</span>}
                    </div>
                  </div>
                  {isDeptAdmin() && req.status === "pending" && (
                    <div className="flex gap-2 shrink-0">
                      <button onClick={() => handleReview(req.id, "approve")}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg bg-green-500/10 text-green-400 hover:bg-green-500/20 border border-green-500/30 transition-colors">
                        <CheckCircle className="w-3.5 h-3.5" /> Approve
                      </button>
                      <button onClick={() => handleReview(req.id, "reject")}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30 transition-colors">
                        <XCircle className="w-3.5 h-3.5" /> Reject
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 7.1 — Create directory and write the file**

```bash
mkdir -p frontend/src/app/dashboard/admin/access-requests
```
Then write the file as shown above.

- [ ] **Step 7.2 — Verify page loads at `/dashboard/admin/access-requests`**

- [ ] **Step 7.3 — Commit**

```bash
git add frontend/src/app/dashboard/admin/access-requests/page.tsx
git commit -m "feat(access-requests): new page — submit, filter, and review access requests"
```

---

## Task 8 — Replace sidebar.tsx (RBAC-filtered nav + role badge)

**Files:**
- Modify: `frontend/src/components/sidebar.tsx`

Changes: import `useAuth`, filter admin section by `isDeptAdmin()`, show role badge, add Access Requests link for all users.

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "../utils/cn";
import { useAuth } from "../contexts/auth-context";
import {
  Home, MessageSquare, FileUp, Search, Users, Settings,
  Building2, BarChart3, Shield, ChevronLeft, ChevronRight,
  Bot, Microscope, Database, Activity, Plug, ThumbsUp,
  Bell, HardDrive, ClipboardList,
} from "lucide-react";

interface SidebarProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const ROLE_COLORS: Record<string, string> = {
  root: "bg-red-500/20 text-red-400",
  dept_admin: "bg-purple-500/20 text-purple-400",
  power_user: "bg-blue-500/20 text-blue-400",
  user: "bg-green-500/20 text-green-400",
  viewer: "bg-gray-500/20 text-gray-400",
};

const mainNav = [
  { name: "Dashboard", href: "/dashboard", icon: Home },
  { name: "Chat Assistant", href: "/dashboard/chat", icon: MessageSquare },
  { name: "Query Assistant", href: "/dashboard/query", icon: Search },
  { name: "Agent Assistant", href: "/dashboard/agent", icon: Bot },
  { name: "Enhanced Research", href: "/dashboard/research", icon: Microscope },
  { name: "Document Ingest", href: "/dashboard/ingest", icon: FileUp },
  { name: "Index Management", href: "/dashboard/indexes", icon: Database },
  { name: "Analytics", href: "/dashboard/analytics", icon: BarChart3 },
];

const toolsNav = [
  { name: "System Monitoring", href: "/dashboard/monitoring", icon: Activity },
  { name: "MCP Dashboard", href: "/dashboard/mcp", icon: Plug },
  { name: "Feedback Analytics", href: "/dashboard/feedback", icon: ThumbsUp },
  { name: "Access Requests", href: "/dashboard/admin/access-requests", icon: ClipboardList },
];

const adminNav = [
  { name: "Admin Panel", href: "/dashboard/admin", icon: Settings },
  { name: "Departments", href: "/dashboard/admin/departments", icon: Building2 },
  { name: "Users", href: "/dashboard/admin/users", icon: Users },
  { name: "Security", href: "/dashboard/admin/security", icon: Shield },
  { name: "Notifications", href: "/dashboard/admin/notifications", icon: Bell },
  { name: "Storage", href: "/dashboard/admin/storage", icon: HardDrive },
];

export function Sidebar({ open, setOpen }: SidebarProps) {
  const pathname = usePathname();
  const { user, isDeptAdmin, hasPermission } = useAuth();

  const NavLink = ({ item }: { item: { name: string; href: string; icon: React.ElementType } }) => {
    const isActive = pathname === item.href ||
      (item.href !== "/dashboard" && pathname?.startsWith(item.href));
    return (
      <Link href={item.href}
        className={cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
          isActive
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        )}>
        <item.icon className="w-5 h-5 shrink-0" />
        {open && <span className="text-sm font-medium">{item.name}</span>}
      </Link>
    );
  };

  return (
    <nav className={cn(
      "flex flex-col h-screen bg-card border-r border-border transition-all duration-300",
      open ? "w-64" : "w-16"
    )}>
      {/* Logo */}
      <div className="flex items-center h-16 px-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">H</span>
          </div>
          {open && (
            <div className="flex flex-col">
              <span className="font-semibold text-sm">Huron</span>
              <span className="text-xs text-muted-foreground">Knowledge AI</span>
            </div>
          )}
        </div>
      </div>

      {/* Role badge */}
      {open && user && (
        <div className="px-4 py-2 border-b border-border">
          <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", ROLE_COLORS[user.role] || ROLE_COLORS.user)}>
            {user.role} · {user.department}
          </span>
        </div>
      )}

      {/* Navigation */}
      <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {open && <span className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">Main</span>}
        {mainNav
          .filter((item) => {
            if (item.href.includes("analytics") && !hasPermission("analytics")) return false;
            return true;
          })
          .map((item) => <NavLink key={item.name} item={item} />)}

        {open && <span className="px-3 pt-6 text-xs font-medium text-muted-foreground uppercase tracking-wider block">Tools</span>}
        {toolsNav.map((item) => <NavLink key={item.name} item={item} />)}

        {isDeptAdmin() && (
          <>
            {open && <span className="px-3 pt-6 text-xs font-medium text-muted-foreground uppercase tracking-wider block">Admin</span>}
            {adminNav.map((item) => <NavLink key={item.name} item={item} />)}
          </>
        )}
      </div>

      {/* Toggle */}
      <button onClick={() => setOpen(!open)}
        className="flex items-center justify-center h-12 border-t border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
        {open ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
      </button>
    </nav>
  );
}
```

- [ ] **Step 8.1 — Write the complete sidebar.tsx above**

- [ ] **Step 8.2 — Verify sidebar shows role badge and hides admin section for non-admin users**

- [ ] **Step 8.3 — Commit**

```bash
git add frontend/src/components/sidebar.tsx
git commit -m "feat(sidebar): RBAC-filtered nav, role badge, access-requests link for all users"
```

---

## Task 9 — Replace header.tsx (async logout + namespace display)

**Files:**
- Modify: `frontend/src/components/header.tsx`

Change `logout` call to `await logout()` and show the user's Pinecone namespace.

```tsx
"use client";

import { useTheme } from "next-themes";
import { Moon, Sun, Bell, User, Menu, LogOut, Database } from "lucide-react";
import { cn } from "../utils/cn";
import { useAuth } from "../contexts/auth-context";

interface HeaderProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export function Header({ sidebarOpen, setSidebarOpen }: HeaderProps) {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuth();

  const namespace =
    user?.role === "root"
      ? "all namespaces"
      : `vaultmind-huron-${user?.department}-general`;

  const handleLogout = async () => {
    await logout();
  };

  return (
    <header className="flex items-center justify-between h-16 px-6 border-b border-border bg-card">
      <button onClick={() => setSidebarOpen(!sidebarOpen)} className="lg:hidden p-2 rounded-lg hover:bg-accent">
        <Menu className="w-5 h-5" />
      </button>

      {/* Search */}
      <div className="hidden md:flex flex-1 max-w-md mx-8">
        <input
          type="text"
          placeholder="Search documents, policies..."
          className="w-full px-4 py-2 text-sm bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      <div className="flex items-center gap-2">
        {/* Namespace badge */}
        {user && (
          <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-lg bg-muted text-xs text-muted-foreground">
            <Database className="w-3 h-3" />
            <span className="font-mono">{namespace}</span>
          </div>
        )}

        {/* Notifications */}
        <button className="relative p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-destructive rounded-full" />
        </button>

        {/* Theme toggle */}
        <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
          {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        {/* User info */}
        <div className="flex items-center gap-2 p-2 rounded-lg hover:bg-accent">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
            <User className="w-4 h-4 text-primary" />
          </div>
          <div className="hidden md:block text-left">
            <p className="text-sm font-medium">{user?.full_name || user?.username || "User"}</p>
            <p className="text-xs text-muted-foreground capitalize">{user?.role} · {user?.department}</p>
          </div>
        </div>

        {/* Logout */}
        <button onClick={handleLogout}
          className="p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-destructive transition-colors"
          title="Logout">
          <LogOut className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
}
```

- [ ] **Step 9.1 — Write the complete header.tsx above**

- [ ] **Step 9.2 — Verify logout works end-to-end**

Click logout → backend blacklists token → localStorage cleared → redirect to login. Try reusing the old token:
```bash
curl -H "Authorization: Bearer <old-token>" http://localhost:8000/api/v1/auth/validate
# Expected: 401 Invalid or expired token
```

- [ ] **Step 9.3 — Commit**

```bash
git add frontend/src/components/header.tsx
git commit -m "feat(header): async logout with token blacklist, Pinecone namespace badge"
```

---

## Task 10 — End-to-end smoke test

- [ ] **Step 10.1 — Verify login flow**

1. Go to `http://localhost:3000`
2. Log in as `root` / `HuronRoot2026!`
3. Enter any 6-digit MFA code → should reach dashboard

- [ ] **Step 10.2 — Verify RBAC gating**

1. Admin panel (`/dashboard/admin`) shows user table for root
2. Sidebar shows Admin section for root, hides it for viewer
3. Access requests page works for all roles

- [ ] **Step 10.3 — Verify real logout**

1. Click logout
2. Back-button to dashboard → redirected to login
3. Old token rejected by backend (401)

- [ ] **Step 10.4 — Verify untouched pages still work**

Navigate to: Chat, Query, Research, Ingest, Monitoring, Analytics — all should load without errors.

- [ ] **Step 10.5 — Final commit**

```bash
git add -A
git status  # confirm only expected files changed
git commit -m "chore(v3): smoke test passed — all 8 files updated, untouched pages verified"
```

---

## Rollback

If the backend breaks, restore with:
```bash
cp backend/main.py.v2.bak backend/main.py
```
The `huron.db` is a fresh database — if needed, delete it and the old `users.db` remains untouched.

---

## Notes

- **Root credentials:** `root` / `HuronRoot2026!` (seeded by `init_db()`)
- **DB location:** `data/huron.db` (new, separate from existing `data/users.db`)
- **MFA dev mode:** any 6-digit code works when no `pending_token` is provided (dev bypass in Task 1 Step 1.3)
- **EmailStr:** The v3 backend import includes `EmailStr` from pydantic but uses plain `str` in models — safe to leave or remove unused import
- **AdminPanel component:** `components/Admin/AdminPanel.tsx` is now unused but left intact; safe to delete later
