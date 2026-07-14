"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { LoadingSpinner } from "./ui";
import { useCurrentUser } from "@/hooks";

interface AuthGuardProps {
  children: React.ReactNode;
  requiredRole?: "admin" | "analyst" | "viewer";
}

export function AuthGuard({ children, requiredRole }: AuthGuardProps) {
  const router = useRouter();
  const token = typeof window !== "undefined" ? Cookies.get("access_token") : null;
  const { data: user, isLoading, isError } = useCurrentUser();

  useEffect(() => {
    if (!token) {
      router.replace("/auth/login");
      return;
    }
    if (isError) {
      router.replace("/auth/login");
    }
  }, [token, isError, router]);

  useEffect(() => {
    if (!user || !requiredRole) return;
    const hierarchy = { admin: 3, analyst: 2, viewer: 1 };
    if ((hierarchy[user.role] ?? 0) < (hierarchy[requiredRole] ?? 0)) {
      router.replace("/dashboard");
    }
  }, [user, requiredRole, router]);

  if (!token || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return <>{children}</>;
}
