"use client";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import {
  LayoutDashboard, Zap, Upload,
  AlertTriangle, Cpu, LogOut, Users,
  ClipboardList, CreditCard, Settings,
} from "lucide-react";
import { clsx } from "clsx";

const nav = [
  { label: "Dashboard",    href: "/dashboard",   icon: LayoutDashboard },
  { label: "Predict",      href: "/predict",     icon: Zap             },
  { label: "Upload Batch", href: "/upload",      icon: Upload          },
  { label: "Transactions", href: "/transactions",icon: CreditCard      },
  { label: "Fraud Alerts", href: "/alerts",      icon: AlertTriangle   },
  { label: "Models",       href: "/models",      icon: Cpu             },
  { label: "Settings",     href: "/settings",    icon: Settings        },
];
const adminNav = [
  { label: "Users",      href: "/admin/users",      icon: Users         },
  { label: "Audit Logs", href: "/admin/audit-logs", icon: ClipboardList },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const logout = () => { Cookies.remove("access_token"); Cookies.remove("refresh_token"); router.push("/auth/login"); };

  return (
    <aside className="w-64 bg-surface-container-lowest text-on-surface flex flex-col h-screen sticky top-0 shrink-0 border-r border-outline-variant">
      {/* Logo */}
      <div className="p-5 flex items-center gap-3">
        <Image src="/logo.png" alt="FraudShield AI" width={36} height={36} className="rounded-lg" priority />
        <div>
          <span className="font-headline font-bold text-on-surface text-lg">FraudShield</span>
          <p className="text-xs text-on-surface-dim">v2.0.0</p>
        </div>
      </div>

      <div className="mx-4 border-t border-outline-variant" />

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-0.5 overflow-y-auto">
        {nav.map(({ label, href, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link key={href} href={href} className={clsx(
              "flex items-center gap-3 px-3 py-2.5 rounded-md text-body-md font-medium transition-all duration-200",
              active
                ? "bg-secondary-container text-on-secondary-container"
                : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
            )}>
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          );
        })}

        <div className="pt-4 mt-2 border-t border-outline-variant">
          <p className="text-label-sm text-on-surface-dim px-3 mb-2 uppercase tracking-wider">Admin</p>
          {adminNav.map(({ label, href, icon: Icon }) => {
            const active = pathname.startsWith(href);
            return (
              <Link key={href} href={href} className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-body-md font-medium transition-all duration-200",
                active
                  ? "bg-secondary-container text-on-secondary-container"
                  : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
              )}>
                <Icon className="w-4 h-4 shrink-0" />
                {label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Logout */}
      <div className="p-4 border-t border-outline-variant">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-md text-body-md font-medium text-on-surface-variant hover:bg-surface-container hover:text-error transition-all duration-200"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
