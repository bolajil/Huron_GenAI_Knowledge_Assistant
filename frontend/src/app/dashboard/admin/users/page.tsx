"use client";

import { Users, Plus, Search, Shield, Mail } from "lucide-react";

const users = [
  { name: "Admin User", email: "admin@vaultmind.ai", role: "admin", dept: "IT", status: "active" },
  { name: "Jane Smith", email: "jane.smith@huron.com", role: "power_user", dept: "Legal", status: "active" },
  { name: "John Doe", email: "john.doe@huron.com", role: "user", dept: "HR", status: "active" },
  { name: "Alice Johnson", email: "alice.j@huron.com", role: "user", dept: "Finance", status: "active" },
  { name: "Bob Wilson", email: "bob.w@huron.com", role: "viewer", dept: "Clinical", status: "inactive" },
];

export default function UsersPage() {
  return (
    <div className="space-y-6">
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
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg">
          <Plus className="h-4 w-4" />
          Add User
        </button>
      </div>

      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input 
            placeholder="Search users..."
            className="w-full pl-10 pr-4 py-2 rounded-lg bg-background border border-border"
          />
        </div>
        <select className="px-4 py-2 rounded-lg bg-background border border-border">
          <option>All Departments</option>
          <option>HR</option>
          <option>Legal</option>
          <option>Finance</option>
        </select>
      </div>

      {/* Users Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
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
            {users.map((user, idx) => (
              <tr key={idx} className="border-t border-border hover:bg-muted/30">
                <td className="p-4">
                  <div>
                    <p className="font-medium">{user.name}</p>
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {user.email}
                    </p>
                  </div>
                </td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded text-xs ${
                    user.role === 'admin' ? 'bg-red-500/10 text-red-500' :
                    user.role === 'power_user' ? 'bg-purple-500/10 text-purple-500' :
                    user.role === 'user' ? 'bg-blue-500/10 text-blue-500' :
                    'bg-gray-500/10 text-gray-500'
                  }`}>
                    {user.role}
                  </span>
                </td>
                <td className="p-4">{user.dept}</td>
                <td className="p-4">
                  <span className={`flex items-center gap-1 text-sm ${
                    user.status === 'active' ? 'text-green-500' : 'text-gray-500'
                  }`}>
                    <span className={`w-2 h-2 rounded-full ${
                      user.status === 'active' ? 'bg-green-500' : 'bg-gray-500'
                    }`}></span>
                    {user.status}
                  </span>
                </td>
                <td className="p-4">
                  <button className="p-2 hover:bg-accent rounded-lg">
                    <Shield className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
