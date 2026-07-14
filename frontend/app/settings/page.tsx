"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Sidebar } from "@/components/shared/Sidebar";
import { Topbar } from "@/components/shared/Topbar";
import { useCurrentUser, useModels } from "@/hooks";
import toast from "react-hot-toast";
import { User, Lock, Sliders, Save, RefreshCw } from "lucide-react";

export default function SettingsPage() {
  const qc = useQueryClient();
  const { data: user } = useCurrentUser();
  const { data: models = [] } = useModels();
  const activeModel = models.find((m) => m.is_active);
  const storedThreshold = typeof activeModel?.hyperparams?.threshold === "number"
    ? activeModel.hyperparams.threshold as number : 0.5;

  const [fullName, setFullName] = useState("");
  const [passwords, setPasswords] = useState({ next: "", confirm: "" });
  const [threshold, setThreshold] = useState(storedThreshold);

  const profileMutation = useMutation({
    mutationFn: (d: { full_name?: string }) => api.put("/auth/me", d).then((r) => r.data),
    onSuccess: () => { toast.success("Profile updated"); qc.invalidateQueries({ queryKey: ["me"] }); },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Update failed"),
  });

  const passwordMutation = useMutation({
    mutationFn: (d: { password: string }) => api.put("/auth/me", d).then((r) => r.data),
    onSuccess: () => { toast.success("Password changed"); setPasswords({ next: "", confirm: "" }); },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Failed"),
  });

  const thresholdMutation = useMutation({
    mutationFn: (t: number) => api.post(`/models/threshold?threshold=${t}`).then((r) => r.data),
    onSuccess: (d) => { toast.success(`Threshold -> ${(d.threshold*100).toFixed(0)}%`); qc.invalidateQueries({ queryKey: ["models"] }); },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Failed"),
  });

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <Topbar title="Settings" subtitle="Profile and system preferences" />
        <div className="max-w-2xl space-y-6">

          {/* Profile */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 bg-primary-container rounded-xl flex items-center justify-center">
                <User className="w-5 h-5 text-primary" />
              </div>
              <div><h2 className="text-sm font-semibold text-on-surface">Profile</h2>
                <p className="text-xs text-on-surface-dim">Update your display name</p></div>
            </div>
            <div className="space-y-4">
              <div><label className="label">Full name</label>
                <input className="input" placeholder={user?.full_name ?? "Your name"}
                  value={fullName} onChange={(e) => setFullName(e.target.value)} /></div>
              <div><label className="label">Email</label>
                <input className="input bg-surface-container cursor-not-allowed" value={user?.email ?? ""} disabled /></div>
              <div><label className="label">Role</label>
                <input className="input bg-surface-container cursor-not-allowed capitalize" value={user?.role ?? ""} disabled /></div>
              <button disabled={profileMutation.isPending || !fullName}
                onClick={() => profileMutation.mutate({ full_name: fullName })}
                className="btn-primary flex items-center gap-2">
                <Save className="w-4 h-4" />{profileMutation.isPending ? "Saving..." : "Save profile"}
              </button>
            </div>
          </div>

          {/* Password */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 bg-surface-warning rounded-xl flex items-center justify-center">
                <Lock className="w-5 h-5 text-warning" />
              </div>
              <div><h2 className="text-sm font-semibold text-on-surface">Change password</h2>
                <p className="text-xs text-on-surface-dim">Min 8 characters</p></div>
            </div>
            <div className="space-y-4">
              <div><label className="label">New password</label>
                <input type="password" minLength={8} className="input" placeholder="Min 8 characters"
                  value={passwords.next} onChange={(e) => setPasswords({ ...passwords, next: e.target.value })} /></div>
              <div><label className="label">Confirm password</label>
                <input type="password" className="input" placeholder="Repeat password"
                  value={passwords.confirm} onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })} />
                {passwords.next && passwords.confirm && passwords.next !== passwords.confirm && (
                  <p className="text-xs text-error mt-1">Passwords do not match</p>)}
              </div>
              <button
                disabled={passwordMutation.isPending || !passwords.next || passwords.next !== passwords.confirm}
                onClick={() => passwordMutation.mutate({ password: passwords.next })}
                className="btn-primary flex items-center gap-2">
                <Lock className="w-4 h-4" />{passwordMutation.isPending ? "Changing..." : "Change password"}
              </button>
            </div>
          </div>

          {/* Threshold */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 bg-primary-container rounded-xl flex items-center justify-center">
                <Sliders className="w-5 h-5 text-primary" />
              </div>
              <div><h2 className="text-sm font-semibold text-on-surface">Decision threshold</h2>
                <p className="text-xs text-on-surface-dim">Probability cutoff for flagging fraud. Lower = more alerts.</p></div>
            </div>
            {activeModel ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-on-surface-variant">Current threshold</span>
                  <span className="text-2xl font-bold text-secondary">{(threshold*100).toFixed(0)}%</span>
                </div>
                <input type="range" min={10} max={95} step={1} className="w-full accent-secondary"
                  value={Math.round(threshold*100)} onChange={(e) => setThreshold(parseInt(e.target.value)/100)} />
                <div className="flex justify-between text-xs text-on-surface-dim">
                  <span>10% (sensitive)</span><span>50% (balanced)</span><span>95% (conservative)</span>
                </div>
                <div className="flex gap-3">
                  <button onClick={() => thresholdMutation.mutate(threshold)}
                    disabled={thresholdMutation.isPending}
                    className="btn-primary flex items-center gap-2 text-sm">
                    <Save className="w-4 h-4" />{thresholdMutation.isPending ? "Updating..." : "Apply"}
                  </button>
                  <button onClick={() => setThreshold(0.5)} className="btn-secondary text-sm flex items-center gap-2">
                    <RefreshCw className="w-4 h-4" />Reset to 50%
                  </button>
                </div>
                <p className="text-xs text-on-surface-dim">Active: <span className="font-mono">{activeModel.version_tag}</span></p>
              </div>
            ) : (
              <p className="text-sm text-on-surface-dim py-4 text-center">
                No active model. <a href="/models" className="text-tertiary hover:underline">Activate one first.</a>
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
