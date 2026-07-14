"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { User } from "@/types";
import { Sidebar } from "@/components/shared/Sidebar";
import toast from "react-hot-toast";
import { Users, Shield, UserCheck, UserX } from "lucide-react";
import { clsx } from "clsx";
import { formatDistanceToNow } from "date-fns";

const ROLE_COLORS: Record<string, string> = {
  admin:   "bg-primary-container text-primary",
  analyst: "bg-secondary-container text-secondary",
  viewer:  "bg-surface-container text-on-surface-dim",
};

export default function AdminUsersPage() {
  const qc = useQueryClient();

  const { data: users = [], isLoading } = useQuery<User[]>({
    queryKey: ["admin-users"],
    queryFn: () => api.get("/admin/users?limit=200").then((r) => r.data),
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/admin/users/${id}`, { is_active }).then((r) => r.data),
    onSuccess: (data: User) => {
      toast.success(`${data.full_name} ${data.is_active ? "activated" : "deactivated"}`);
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: () => toast.error("Update failed"),
  });

  const changeRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      api.patch(`/admin/users/${id}`, { role }).then((r) => r.data),
    onSuccess: (data: User) => {
      toast.success(`${data.full_name} -> ${data.role}`);
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-6">
          <h1 className="text-headline-md font-headline font-bold text-on-surface">User Management</h1>
          <p className="text-body-md text-on-surface-variant mt-1">{users.length} users registered</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: "Total Users", value: users.length,                                icon: Users,     color: "bg-secondary" },
            { label: "Active",      value: users.filter((u) => u.is_active).length,     icon: UserCheck, color: "bg-success" },
            { label: "Inactive",    value: users.filter((u) => !u.is_active).length,    icon: UserX,     color: "bg-on-surface-dim" },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="card p-4 flex items-center gap-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
                <Icon className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-xl font-bold text-on-surface">{value}</p>
                <p className="text-xs text-on-surface-dim">{label}</p>
              </div>
            </div>
          ))}
        </div>

        {isLoading ? (
          <div className="flex justify-center pt-20">
            <div className="w-8 h-8 border-4 border-secondary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="table-header">
                <tr>
                  {["Name", "Email", "Role", "Status", "Joined", "Actions"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-on-surface-dim uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-surface-container transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-primary-container text-primary rounded-full flex items-center justify-center text-xs font-bold">
                          {user.full_name.charAt(0).toUpperCase()}
                        </div>
                        <span className="font-medium text-on-surface">{user.full_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-on-surface-variant">{user.email}</td>
                    <td className="px-4 py-3">
                      <select
                        value={user.role}
                        onChange={(e) => changeRole.mutate({ id: user.id, role: e.target.value })}
                        className={clsx("text-xs font-medium px-2 py-1 rounded-full border-0 cursor-pointer", ROLE_COLORS[user.role])}
                      >
                        <option value="admin">admin</option>
                        <option value="analyst">analyst</option>
                        <option value="viewer">viewer</option>
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium",
                        user.is_active ? "bg-surface-success text-success" : "bg-surface-error text-error")}>
                        {user.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-on-surface-dim">
                      {formatDistanceToNow(new Date(user.created_at), { addSuffix: true })}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => toggleActive.mutate({ id: user.id, is_active: !user.is_active })}
                        className={clsx("text-xs font-medium",
                          user.is_active ? "text-error hover:text-error" : "text-success hover:text-success")}
                      >
                        {user.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
