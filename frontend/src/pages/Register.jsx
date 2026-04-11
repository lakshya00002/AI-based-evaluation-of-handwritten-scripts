import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.js";

export default function Register() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    role: "student",
    preferred_language: "en",
  });
  const [err, setErr] = useState("");
  const nav = useNavigate();

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    try {
      await api.register(form);
      nav("/login");
    } catch (ex) {
      setErr(ex.message || "Registration failed");
    }
  }

  return (
    <div className="max-w-md mx-auto bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
      <h1 className="text-2xl font-bold text-ink-950 mb-6">Create account</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Full name</label>
          <input
            className="w-full border border-slate-300 rounded-lg px-3 py-2"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
          <input
            className="w-full border border-slate-300 rounded-lg px-3 py-2"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Password (min 8)</label>
          <input
            className="w-full border border-slate-300 rounded-lg px-3 py-2"
            type="password"
            minLength={8}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
          <select
            className="w-full border border-slate-300 rounded-lg px-3 py-2"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          >
            <option value="student">Student</option>
            <option value="teacher">Teacher</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Preferred language</label>
          <select
            className="w-full border border-slate-300 rounded-lg px-3 py-2"
            value={form.preferred_language}
            onChange={(e) => setForm({ ...form, preferred_language: e.target.value })}
          >
            <option value="en">English</option>
            <option value="hi">Hindi (OCR hint)</option>
          </select>
        </div>
        {err && <p className="text-sm text-red-600">{err}</p>}
        <button type="submit" className="w-full py-2.5 bg-accent text-white rounded-lg font-medium hover:bg-accent-dim">
          Register
        </button>
      </form>
      <p className="text-sm text-slate-600 mt-4">
        Already have an account?{" "}
        <Link to="/login" className="text-accent font-medium">
          Sign in
        </Link>
      </p>
    </div>
  );
}
