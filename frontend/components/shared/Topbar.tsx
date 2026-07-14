"use client";
import { HealthStatusBar } from "./HealthStatusBar";
import { useCurrentUser } from "@/hooks";
import { Bell } from "lucide-react";
import { useAlerts } from "@/hooks";

interface TopbarProps {
  title: string;
  subtitle?: string;
}

export function Topbar({ title, subtitle }: TopbarProps) {
  const { data: user } = useCurrentUser();
  const { data: openAlerts = [] } = useAlerts("open");

  return (
    <div className="flex items-center justify-between pb-6 border-b border-outline-variant mb-6">
      <div>
        <h1 className="text-headline-md font-headline font-bold text-on-surface">{title}</h1>
        {subtitle && <p className="text-body-md text-on-surface-variant mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-4">
        <HealthStatusBar />

        {/* Alert bell */}
        <a href="/alerts" className="relative p-2 rounded-md hover:bg-surface-container transition-colors">
          <Bell className="w-5 h-5 text-on-surface-variant" />
          {openAlerts.length > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 bg-error rounded-full text-white text-[10px] font-bold flex items-center justify-center">
              {openAlerts.length > 9 ? "9+" : openAlerts.length}
            </span>
          )}
        </a>

        {/* User avatar */}
        {user && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-secondary-container text-on-secondary-container rounded-full flex items-center justify-center text-sm font-bold">
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div className="hidden md:block">
              <p className="text-body-md font-medium text-on-surface leading-none">{user.full_name}</p>
              <p className="text-xs text-on-surface-dim capitalize mt-0.5">{user.role}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
