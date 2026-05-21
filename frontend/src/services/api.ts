const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ───────────────────────────────────────────────────────────────────

export type UserRole = "root" | "dept_admin" | "power_user" | "user" | "viewer";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  department: string;
  role: UserRole;
  permissions: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface QueryResponse {
  status: string;
  query: string;
  results: string;
  sources: Array<{ title: string; page?: number }>;
}

export interface IngestResponse {
  status: string;
  document_id: string;
  file: string;
  department: string;
  namespace: string;
  parent_chunks: number;
  child_chunks: number;
  pinecone_upsert: boolean;
  warnings: string[];
}

export interface StatsResponse {
  total_documents: number;
  queries_today: number;
  active_users: number;
  avg_response_time: number;
  total_users: number;
  departments: number;
}

export interface RecentQuery {
  id: number;
  username: string;
  department: string;
  query_text: string;
  response_time_ms: number;
  timestamp: string;
}

export interface Department {
  id: number;
  code: string;
  display_name: string;
  namespace: string;
  classification?: string;
  user_count?: number;
}

export interface CreateUserPayload {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  department_id: string;
}

export interface AccessRequest {
  id: number;
  requester_id: number;
  requester_name: string;
  requester_email: string;
  dept_code: string;
  requested_tab: string;
  requested_role: string;
  justification: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  reviewer_name?: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const getAuthHeader = (): HeadersInit => {
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

// ─── API Client ──────────────────────────────────────────────────────────────

export const api = {
  // ── Auth ────────────────────────────────────────────────────────────────────

  async login(username: string, password: string, authMethod = "local"): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, auth_method: authMethod }),
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Login failed");
    }
    return response.json();
  },

  async validateToken(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/validate`, {
        headers: getAuthHeader(),
      });
      return response.ok;
    } catch {
      return false;
    }
  },

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
        method: "POST",
        headers: getAuthHeader(),
      });
    } finally {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user");
      localStorage.removeItem("mfa_verified");
    }
  },

  // ── Root admin ───────────────────────────────────────────────────────────────

  async rootListAllUsers(): Promise<{ users: User[] }> {
    return request("/api/v1/root/users");
  },

  async rootCreateUser(payload: CreateUserPayload): Promise<{ status: string; user: User }> {
    return request("/api/v1/root/users", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async rootUpdateUser(
    userId: number,
    updates: Partial<Pick<User, "role" | "department"> & { is_active: boolean }>
  ): Promise<{ status: string }> {
    return request(`/api/v1/root/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  },

  async rootDeleteUser(userId: number): Promise<{ status: string }> {
    return request(`/api/v1/root/users/${userId}`, { method: "DELETE" });
  },

  async rootListDepartments(): Promise<{ departments: Department[] }> {
    return request("/api/v1/root/departments");
  },

  // ── Dept admin ───────────────────────────────────────────────────────────────

  async deptListUsers(): Promise<{ users: User[] }> {
    return request("/api/v1/dept-admin/users");
  },

  async deptCreateUser(
    payload: Omit<CreateUserPayload, "role"> & { role?: UserRole }
  ): Promise<{ status: string; user: User }> {
    return request("/api/v1/dept-admin/users", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // ── Stats ────────────────────────────────────────────────────────────────────

  async getStats(): Promise<StatsResponse> {
    return request("/api/v1/admin/stats");
  },

  async getRecentQueries(limit = 10): Promise<{ queries: RecentQuery[] }> {
    return request(`/api/v1/admin/stats/recent-queries?limit=${limit}`);
  },

  // ── Access requests ──────────────────────────────────────────────────────────

  async listRequestableTabs(): Promise<{
    tabs: Array<{ tab: string; label: string; description: string; currently_accessible: boolean }>;
    user_role: string;
  }> {
    return request("/api/v1/access-requests/tabs");
  },

  async submitAccessRequest(
    requested_tab: string,
    justification: string,
    dept_code: string,
    requested_role = "user"
  ): Promise<{ status: string; request_id: number }> {
    return request("/api/v1/access-requests", {
      method: "POST",
      body: JSON.stringify({ requested_tab, justification, dept_code, requested_role }),
    });
  },

  async listAccessRequests(
    status?: "pending" | "approved" | "rejected"
  ): Promise<{ requests: AccessRequest[] }> {
    const qs = status ? `?status=${status}` : "";
    return request(`/api/v1/access-requests${qs}`);
  },

  async reviewAccessRequest(
    requestId: number,
    action: "approve" | "reject"
  ): Promise<{ status: string }> {
    return request("/api/v1/access-requests/review", {
      method: "POST",
      body: JSON.stringify({ request_id: requestId, action }),
    });
  },

  // ── Query / Chat / Ingest ────────────────────────────────────────────────────

  async query(queryText: string, department = "general", topK = 10): Promise<QueryResponse> {
    return request("/api/v1/query", {
      method: "POST",
      body: JSON.stringify({ query: queryText, department, top_k: topK }),
    });
  },

  async chat(
    messages: Array<{ role: string; content: string }>,
    indexName = "default_faiss"
  ): Promise<{ status: string; response: string; sources: unknown[] }> {
    return request("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ messages, index_name: indexName }),
    });
  },

  async ingestDocument(
    file: File,
    department = "general",
    sensitivityLevel = "internal"
  ): Promise<IngestResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("department", department);
    formData.append("sensitivity_level", sensitivityLevel);

    const response = await fetch(`${API_BASE_URL}/api/v1/ingest`, {
      method: "POST",
      headers: getAuthHeader(),
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Upload failed");
    }
    return response.json();
  },

  // ── Health ───────────────────────────────────────────────────────────────────

  async healthCheck(): Promise<{ status: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.json();
  },
};

export default api;
