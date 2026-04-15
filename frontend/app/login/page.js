"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { getMe, login } from "../../lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login({ email, password });
      const { data } = await getMe();
      router.push(data.role === "teacher" ? "/teacher" : "/student");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center">
      <form onSubmit={onSubmit} className="bg-white shadow rounded p-6 w-full max-w-md space-y-4">
        <h1 className="text-2xl font-bold">Login</h1>
        <input className="w-full border p-2 rounded" placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="w-full border p-2 rounded" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button className="w-full bg-blue-600 text-white p-2 rounded disabled:opacity-50" disabled={loading}>
          {loading ? "Logging in..." : "Login"}
        </button>
        <p className="text-sm">No account? <Link href="/signup" className="text-blue-600">Sign up</Link></p>
      </form>
    </main>
  );
}
