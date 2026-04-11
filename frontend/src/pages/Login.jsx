import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const { setToken, setUserEmail } = useAuth();
  const nav = useNavigate();

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    try {
      const t = await api.token(email, password);
      setToken(t.access_token);
      setUserEmail(email);
      nav("/upload");
    } catch (ex) {
      setErr(ex.message || "Login failed");
    }
  }

  return (
    <div className="max-w-md mx-auto bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
      <h1 className="text-2xl font-bold text-ink-950 mb-2">Sign in</h1>
      <p className="text-slate-600 text-sm mb-6">
        Use your institutional email. Demo: <code className="bg-slate-100 px-1 rounded">student@demo.edu</code>
      </p>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
          <input
            className="w-full border border-slate-300 rounded-lg px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
          <input
            className="w-full border border-slate-300 rounded-lg px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            required
          />
        </div>
        {err && <p className="text-sm text-red-600">{err}</p>}
        <button type="submit" className="w-full py-2.5 bg-accent text-white rounded-lg font-medium hover:bg-accent-dim">
          Continue
        </button>
      </form>
      <p className="text-sm text-slate-600 mt-4">
        No account?{" "}
        <Link to="/register" className="text-accent font-medium">
          Register
        </Link>
      </p>
    </div>
  );
}
