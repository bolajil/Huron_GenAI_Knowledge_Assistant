"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Users,
  Plus,
  Search,
  ShieldCheck,
  ShieldAlert,
  Building2,
  UserX,
  UserCheck,
  Loader2,
} from "lucide-react";
import { useAuth } from "../../../contexts/auth-context";
import { api } from "../../../services/api";
import type { User, UserRole, Department, CreateUserPayload } from "../../../services/api";

const ROLE_BADGE: Record<UserRole, { label: string; cls: string }> = {
  root:        { label: "Root",       cls: "bg-red-500/15 text-red-600 dark:text-red-400" },
  dept_admin:  { label: "Dept Admin", cls: "bg-orange-500/15 text-orange-600 dark:text-orange-400" },
  power_user:  { label: "Power",      cls: "bg-blue-500/15 text-blue-600 dark:text-blue-400" },
  user:        { label: "User",       cls: "bg-green-500/15 text-green-600 dark:text-green-400" },
  viewer:      { label: "Viewer",     cls: "bg-gray-500/15 text-gray-600 dark:text-gray-400" },
};

const ASSIGNABLE_ROLES: UserRole[] = ["dept_admin", "power_user", "user", "viewer"];

function RoleBadge({ role }: { role: UserRole }) {
  const { label, cls } = ROLE_BADGE[role] ?? ROLE_BADGE.viewer;
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>{label}</span>
  );
}

interface CreateUserForm {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  department_id: string;
}

const EMPTY_FORM: CreateUserForm = {
  username: "",
  email: "",
  full_name: "",
  password: "",
  role: "user",
  department_id: "",
};

export default function AdminPage() {
  const { user: currentUser, isRoot, isDeptAdmin } = useAuth();

  const [users, setUsers] = useState<User[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateUserForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    try {
      if (isRoot()) {
        const [usersRes, deptsRes] = await Promise.all([
          api.rootListAllUsers(),
          api.rootListDepartments(),
        ]);
        setUsers(usersRes.users);
        setDepartments(deptsRes.departments);
      } else if (isDeptAdmin()) {
        const usersRes = await api.deptListUsers();
        setUsers(usersRes.users);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, [isRoot, isDeptAdmin]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload: CreateUserPayload = {
        ...form,
        department_id: form.department_id || currentUser?.department || "",
      };
      if (isRoot()) {
        await api.rootCreateUser(payload);
      } else {
        await api.deptCreateUser(payload);
      }
      setForm(EMPTY_FORM);
      setShowCreate(false);
      await fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create user");
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (u: User) => {
    try {
      if (isRoot()) {
        await api.rootUpdateUser(Number(u.id), { is_active: false });
      }
      await fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    }
  };

  const filtered = users.filter(
    (u) =>
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase()) ||
      u.full_name.toLowerCase().includes(search.toLowerCase())
  );

  if (!isDeptAdmin()) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
        <ShieldAlert className="w-10 h-10" />
        <p className="font-medium">Access denied — Admin or higher required</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-primary" />
            User Management
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {isRoot()
              ? "All departments — root access"
              : `Department: ${currentUser?.department}`}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add User
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-red-600 dark:text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Create user form */}
      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="rounded-xl border border-border bg-card p-6 space-y-4"
        >
          <h2 className="font-semibold flex items-center gap-2">
            <Plus className="w-4 h-4" /> New User
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(
              [
                ["full_name", "Full Name"],
                ["username", "Username"],
                ["email", "Email"],
                ["password", "Password"],
              ] as const
            ).map(([field, label]) => (
              <div key={field}>
                <label className="block text-xs text-muted-foreground mb-1">{label}</label>
                <input
                  type={field === "password" ? "password" : "text"}
                  required
                  value={form[field]}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>
            ))}

            <div>
              <label className="block text-xs text-muted-foreground mb-1">Role</label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                {(isRoot() ? (["dept_admin", ...ASSIGNABLE_ROLES] as UserRole[]) : ASSIGNABLE_ROLES).map((r) => (
                  <option key={r} value={r}>
                    {ROLE_BADGE[r].label}
                  </option>
                ))}
              </select>
            </div>

            {isRoot() && departments.length > 0 && (
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Department</label>
                <select
                  value={form.department_id}
                  onChange={(e) => setForm({ ...form, department_id: e.target.value })}
                  required
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                >
                  <option value="">Select department…</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={() => { setShowCreate(false); setForm(EMPTY_FORM); setError(""); }}
              className="px-4 py-2 rounded-lg border border-border text-sm hover:bg-accent transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              Create User
            </button>
          </div>
        </form>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search users…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
      </div>

      {/* User table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40 gap-2 text-muted-foreground">
            <Loader2 className="w-5 h-5 animate-spin" />
            Loading users…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
            <Users className="w-8 h-8" />
            <p className="text-sm">No users found</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/40">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">User</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Role</th>
                {isRoot() && (
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">
                    <Building2 className="w-3.5 h-3.5 inline mr-1" />
                    Dept
                  </th>
                )}
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((u) => (
                <tr key={u.id} className="hover:bg-accent/30 transition-colors">
                  <td className="px-4 py-3">
                    <p className="font-medium">{u.full_name}</p>
                    <p className="text-xs text-muted-foreground">{u.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <RoleBadge role={u.role} />
                  </td>
                  {isRoot() && (
                    <td className="px-4 py-3 text-xs text-muted-foreground capitalize">
                      {u.department}
                    </td>
                  )}
                  <td className="px-4 py-3 text-right">
                    {u.id !== currentUser?.id && u.role !== "root" && (
                      <button
                        onClick={() => handleToggleActive(u)}
                        title="Deactivate user"
                        className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors"
                      >
                        <UserX className="w-4 h-4" />
                      </button>
                    )}
                    {u.id === currentUser?.id && (
                      <UserCheck className="w-4 h-4 text-green-500 inline" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        Showing {filtered.length} of {users.length} users
      </p>
    </div>
  );
}
