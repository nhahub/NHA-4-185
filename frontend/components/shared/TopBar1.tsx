"use client";
import { useCurrentUser, useHealth, useLogout } from "@/hooks";
import { HealthDot } from "./ui";
import { Bell, LogOut, User } from "lucide-react";
import { useState } from "react";
import { clsx } from "clsx";

export function TopBar({ title }: { title?: string }) {
  const { data: user } = useCurrentUser();
  const { data: health } = useHealth();
  const logout = useLogout();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="h-14 bg-surface-container-lowest border-b border-outline-variant flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="text-sm font-medium text-on-surface-variant">{title}</div>

      <div className="flex items-center gap-4">
        {health && (
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-on-surface-dim">
            <HealthDot status={health.status} />
            <span className="capitalize">{health.status}</span>
          </div>
        )}

        <button className="relative text-on-surface-dim hover:text-on-surface transition-colors">
          <Bell className="w-5 h-5" />
        </button>

        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-2 text-sm"
          >
            <div className="w-8 h-8 bg-secondary-container text-on-secondary-container rounded-full flex items-center justify-center font-bold text-xs">
              {user?.full_name?.charAt(0).toUpperCase() ?? "?"}
            </div>
            <span className="hidden md:block font-medium text-on-surface">{user?.full_name}</span>
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-10 z-20 bg-surface-container-high border border-outline-variant rounded-xl w-52 py-1 overflow-hidden">
                <div className="px-4 py-3 border-b border-outline-variant">
                  <p className="text-sm font-semibold text-on-surface truncate">{user?.full_name}</p>
                  <p className="text-xs text-on-surface-dim truncate">{user?.email}</p>
                  <span className={clsx(
                    "inline-block mt-1 text-xs px-2 py-0.5 rounded-full capitalize font-medium",
                    user?.role === "admin" ? "bg-primary-container text-primary" : "bg-secondary-container text-secondary"
                  )}>
                    {user?.role}
                  </span>
                </div>
                <button
                  onClick={logout}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-error hover:bg-surface-error transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
