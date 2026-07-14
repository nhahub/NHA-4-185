"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import Cookies from "js-cookie";
import toast from "react-hot-toast";
import Image from "next/image";

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", form);
      Cookies.set("access_token", data.access_token, { expires: 1 });
      Cookies.set("refresh_token", data.refresh_token, { expires: 7 });
      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="card w-full max-w-md p-8">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <Image src="/logo.png" alt="FraudShield AI" width={40} height={40} className="rounded-xl" priority />
          <div>
            <h1 className="text-xl font-headline font-bold text-on-surface">FraudShield</h1>
            <p className="text-xs text-on-surface-variant">ML Fraud Detection Platform</p>
          </div>
        </div>

        <h2 className="text-headline-md font-headline font-semibold text-on-surface mb-2">Sign in</h2>
        <p className="text-body-md text-on-surface-variant mb-6">Enter your credentials to access the dashboard</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Email address</label>
            <input
              type="email" required className="input"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="analyst@company.com"
            />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              type="password" required className="input"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="••••••••"
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-body-md text-on-surface-variant">
          Don&apos;t have an account?{" "}
          <a href="/auth/register" className="text-tertiary font-medium hover:underline">
            Register
          </a>
        </p>
      </div>
    </div>
  );
}
