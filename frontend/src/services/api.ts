/**
 * VaultMind API Client
 * Per FRONTEND_MIGRATION_GUIDE.md - services/api.js
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  department: string;
  role: string;
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

// Helper to get auth header
const getAuthHeader = (): HeadersInit => {
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// API Client
export const api = {
  // ============== Auth ==============
  
  async login(username: string, password: string, authMethod: string = "local"): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        password,
        auth_method: authMethod,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Login failed");
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
    await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: getAuthHeader(),
    });
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user");
  },

  // ============== Query ==============
  
  async query(
    queryText: string,
    indexName: string = "default_faiss",
    topK: number = 5
  ): Promise<QueryResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(),
      },
      body: JSON.stringify({
        query: queryText,
        index_name: indexName,
        top_k: topK,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Query failed");
    }

    return response.json();
  },

  // ============== Chat ==============
  
  async chat(
    messages: Array<{ role: string; content: string }>,
    indexName: string = "default_faiss"
  ): Promise<{ status: string; response: string; sources: any[] }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(),
      },
      body: JSON.stringify({
        messages,
        index_name: indexName,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Chat failed");
    }

    return response.json();
  },

  // ============== Ingestion ==============
  
  async ingestDocument(
    file: File,
    indexName: string = "default_faiss",
    department?: string
  ): Promise<{ status: string; message: string }> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("index_name", indexName);
    if (department) formData.append("department", department);

    const response = await fetch(`${API_BASE_URL}/api/v1/ingest`, {
      method: "POST",
      headers: getAuthHeader(),
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Upload failed");
    }

    return response.json();
  },

  // ============== Admin ==============
  
  async getUsers(): Promise<{ users: User[] }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/admin/users`, {
      headers: getAuthHeader(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch users");
    }

    return response.json();
  },

  async getStats(): Promise<{
    total_documents: number;
    queries_today: number;
    active_users: number;
    avg_response_time: number;
  }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/admin/stats`, {
      headers: getAuthHeader(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch stats");
    }

    return response.json();
  },

  // ============== Health ==============
  
  async healthCheck(): Promise<{ status: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.json();
  },
};

export default api;
