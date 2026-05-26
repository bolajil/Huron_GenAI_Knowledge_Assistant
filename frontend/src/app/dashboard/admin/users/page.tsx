"use client";

import {
  Users,
  Plus,
  Search,
  Shield,
  Mail,
  X,
  Loader2,
  AlertCircle,
  CheckCircle,
  UserCog,
  Trash2,
} from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { api, User, UserRole, CreateUserPayload } from "@/services/api";
import { useAuth } from "@/contexts/auth-context";

const ROLE_COLORS: Record<string, string> = {
  root:       "bg-red-500/10 text-red-500 border-red-500/20",
  admin:      "bg-red-500/10 text-red-500 border-red-500/20",
  dept_admin: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  power_user: "bg-purple-500/10 text-purple-500 border-purple-500/20",
  user:       "bg-blue-500/10 text-blue-500 border-blue-500/20",
  viewer:     "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

const ROLES: UserRole[] = ["dept_admin", "power_user", "user", "viewer"];

const DEPARTMENTS = [
  "general", "hr", "finance", "legal", "clinical", "operations", "it", "marketing",
];

const emptyForm = (): CreateUserPayload => ({
  username: "",
  email: "",
  full_name: "",
  password: "",
  role: "user",
  department: "general",
});

export default function UsersPage() {
  const { user: me } = useAuth();

  const [users, setUsers]       = useState<User[]>([]);
  const [loading, setLoading]   = useState(true);
  const [fetchErr, setFetchErr] = useState<string | null>(null);

  // Search / filter
  const [search, setSearch]     = useState("");
  const [deptFilter, setDeptFilter] = useState("all");

  // Add User modal
  const [showModal, setShowModal] = useState(false);
  const [form, setForm]           = useState<CreateUserPayload>(emptyForm());
  const [submitting, setSubmitting] = useState(false);
  const [modalErr, setModalErr]     = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Edit status modal
  const [editUser, setEditUser]     = useState<User | null>(null);
  const [editRole, setEditRole]     = useState<UserRole>("user");
  const [editActive, setEditActive] = useState(true);
  const [editSaving, setEditSaving] = useState(false);
  const [editErr, setEditErr]       = useState<string | null>(null);

  const firstInputRef = useRef<HTMLInputElement>(null);

  const fetchUsers = async () => {
    setLoading(true);
    setFetchErr(null);
    try {
      const data = await api.rootListAllUsers();
      setUsers(data.users ?? []);
    } catch (err: unknown) {
      setFetchErr(err instanceof Error ? err.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  // Focus first input when modal opens
  useEffect(() => {
    if (showModal) {
      setTimeout(() => firstInputRef.current?.focus(), 50);
    }
  }, [showModal]);

  // ── Filtering ─────────────────────────────────────────────────────────────
  const filtered = users.filter((u) => {
    const q = search.toLowerCase();
    const matchSearch =
      !q ||
      u.username.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q) ||
      u.full_name?.toLowerCase().includes(q);
    const matchDept =
      deptFilter === "all" || u.department === deptFilter;
    return matchSearch && matchDept;
  });

  // ── Add User ──────────────────────────────────────────────────────────────
  const openAdd = () => {
    setForm(emptyForm());
    setModalErr(null);
    setSuccessMsg(null);
    setShowModal(true);
  };

  const closeAdd = () => {
    if (submitting) return;
    setShowModal(false);
  };

  const handleField = (key: keyof CreateUserPayload, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.username || !form.email || !form.password) {
      setModalErr("Username, email, and password are required.");
      return;
    }
    setSubmitting(true);
    setModalErr(null);
    try {
      await api.rootCreateUser(form);
      setSuccessMsg(`User "${form.username}" created successfully.`);
      setForm(emptyForm());
      await fetchUsers();
      setTimeout(() => {
        setShowModal(false);
        setSuccessMsg(null);
      }, 1500);
    } catch (err: unknown) {
      setModalErr(err instanceof Error ? err.message : "Failed to create user.");
    } finally {
      setSubmitting(false);
    }
  };

  // ── Edit / Deactivate ─────────────────────────────────────────────────────
  const openEdit = (u: User) => {
    setEditUser(u);
    setEditRole(u.role);
    setEditActive(true);  // API doesn't return is_active in User type; assume active
    setEditErr(null);
  };

  const closeEdit = () => { if (!editSaving) setEditUser(null); };

  const handleEditSave = async () => {
    if (!editUser) return;
    setEditSaving(true);
    setEditErr(null);
    try {
      await api.rootUpdateUser(Number(editUser.id), {
        role:      editRole,
        is_active: editActive,
      });
      await fetchUsers();
      setEditUser(null);
    } catch (err: unknown) {
      setEditErr(err instanceof Error ? err.message : "Update failed.");
    } finally {
      setEditSaving(false);
    }
  };

  const handleDelete = async (u: User) => {
    if (!confirm(`Delete user "${u.username}"? This cannot be undone.`)) return;
    try {
      await api.rootDeleteUser(Number(u.id));
      await fetchUsers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Delete failed.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Users className="h-8 w-8 text-blue-500" />
            User Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage users, roles, and permissions
          </p>
        </div>
        <button
          onClick={openAdd}
          className="flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add User
        </button>
      </div>

      {/* Search + Filter */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users..."
            className="w-full pl-10 pr-4 py-2 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <select
          value={deptFilter}
          onChange={(e) => setDeptFilter(e.target.value)}
          className="px-4 py-2 rounded-lg bg-background border border-border focus:outline-none"
        >
          <option value="all">All Departments</option>
          {DEPARTMENTS.map((d) => (
            <option key={d} value={d}>
              {d.charAt(0).toUpperCase() + d.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Fetch error */}
      {fetchErr && (
        <div className="flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 dark:bg-red-950/30 p-3 text-red-600 dark:text-red-400 text-sm">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {fetchErr}
          <button onClick={fetchUsers} className="ml-auto underline text-xs">Retry</button>
        </div>
      )}

      {/* Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading users…
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-muted-foreground text-sm">
            {search || deptFilter !== "all" ? "No users match your filters." : "No users found."}
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-4 font-medium">User</th>
                <th className="text-left p-4 font-medium">Role</th>
                <th className="text-left p-4 font-medium">Department</th>
                <th className="text-left p-4 font-medium">Status</th>
                <th className="text-left p-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id} className="border-t border-border hover:bg-muted/30">
                  <td className="p-4">
                    <p className="font-medium">{u.full_name || u.username}</p>
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {u.email}
                    </p>
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded border text-xs font-medium ${ROLE_COLORS[u.role] ?? ROLE_COLORS.viewer}`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="p-4 capitalize">{u.department}</td>
                  <td className="p-4">
                    <span className="flex items-center gap-1.5 text-sm text-green-500">
                      <span className="w-2 h-2 rounded-full bg-green-500" />
                      active
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => openEdit(u)}
                        title="Edit role / status"
                        className="p-2 hover:bg-accent rounded-lg text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <UserCog className="h-4 w-4" />
                      </button>
                      {me?.role === "root" && u.username !== me.username && (
                        <button
                          onClick={() => handleDelete(u)}
                          title="Delete user"
                          className="p-2 hover:bg-accent rounded-lg text-muted-foreground hover:text-red-500 transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Add User Modal ───────────────────────────────────────────────────── */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                Add New User
              </h2>
              <button onClick={closeAdd} className="p-1.5 hover:bg-accent rounded-lg">
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
              {successMsg && (
                <div className="flex items-center gap-2 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-300 p-3 text-green-700 dark:text-green-400 text-sm">
                  <CheckCircle className="h-4 w-4 shrink-0" />
                  {successMsg}
                </div>
              )}
              {modalErr && (
                <div className="flex items-center gap-2 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-300 p-3 text-red-600 dark:text-red-400 text-sm">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {modalErr}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Full Name</label>
                  <input
                    ref={firstInputRef}
                    value={form.full_name}
                    onChange={(e) => handleField("full_name", e.target.value)}
                    placeholder="Jane Smith"
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Username <span className="text-red-500">*</span></label>
                  <input
                    value={form.username}
                    onChange={(e) => handleField("username", e.target.value)}
                    placeholder="jsmith"
                    required
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Password <span className="text-red-500">*</span></label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => handleField("password", e.target.value)}
                    placeholder="Min 8 characters"
                    required
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Email <span className="text-red-500">*</span></label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => handleField("email", e.target.value)}
                    placeholder="jane@huron.com"
                    required
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Role</label>
                  <select
                    value={form.role}
                    onChange={(e) => handleField("role", e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:outline-none text-sm"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Department</label>
                  <select
                    value={form.department}
                    onChange={(e) => handleField("department", e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:outline-none text-sm"
                  >
                    {DEPARTMENTS.map((d) => (
                      <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeAdd}
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg border border-border hover:bg-accent text-sm font-medium transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium transition-colors disabled:opacity-60 flex items-center gap-2"
                >
                  {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  {submitting ? "Creating…" : "Create User"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Edit User Modal ──────────────────────────────────────────────────── */}
      {editUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-border bg-card shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <UserCog className="h-5 w-5 text-primary" />
                Edit — {editUser.full_name || editUser.username}
              </h2>
              <button onClick={closeEdit} className="p-1.5 hover:bg-accent rounded-lg">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="px-6 py-5 space-y-4">
              {editErr && (
                <div className="flex items-center gap-2 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-300 p-3 text-red-600 dark:text-red-400 text-sm">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {editErr}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium mb-1">Role</label>
                <select
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value as UserRole)}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:outline-none text-sm"
                >
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-3">
                <input
                  id="active-toggle"
                  type="checkbox"
                  checked={editActive}
                  onChange={(e) => setEditActive(e.target.checked)}
                  className="w-4 h-4 rounded accent-primary"
                />
                <label htmlFor="active-toggle" className="text-sm font-medium cursor-pointer">
                  Account active
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-1">
                <button
                  onClick={closeEdit}
                  disabled={editSaving}
                  className="px-4 py-2 rounded-lg border border-border hover:bg-accent text-sm font-medium transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleEditSave}
                  disabled={editSaving}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium transition-colors disabled:opacity-60 flex items-center gap-2"
                >
                  {editSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                  {editSaving ? "Saving…" : "Save Changes"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
