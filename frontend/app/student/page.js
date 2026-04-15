"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "../../components/Sidebar";
import { getAssignments, getMe, getStudentResults, logout, submitAssignment } from "../../lib/api";

const tabs = ["Assignments", "My Results"];

export default function StudentDashboard() {
  const router = useRouter();
  const [active, setActive] = useState("Assignments");
  const [assignments, setAssignments] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submissionState, setSubmissionState] = useState({ assignment_id: "", text: "", file: null });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isPastDue = (dueDate) => {
    if (!dueDate) return false;
    return new Date(dueDate).getTime() < Date.now();
  };

  const load = async () => {
    setLoading(true);
    try {
      const me = await getMe();
      if (me.data.role !== "student") {
        router.replace("/teacher");
        return;
      }
      const [assignmentRes, resultRes] = await Promise.all([getAssignments(), getStudentResults()]);
      setAssignments(assignmentRes.data);
      setResults(resultRes.data);
    } catch {
      router.replace("/login");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    const selected = assignments.find((item) => String(item.id) === String(submissionState.assignment_id));
    if (selected && isPastDue(selected.due_date)) {
      setError("Assignment due date has passed. Submission is closed.");
      return;
    }
    setSubmitting(true);
    try {
      await submitAssignment({
        assignmentId: Number(submissionState.assignment_id),
        text: submissionState.text?.trim() || "",
        file: submissionState.file
      });
      setSubmissionState({ assignment_id: "", text: "", file: null });
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  const onLogout = async () => {
    try {
      await logout();
    } finally {
      router.replace("/login");
    }
  };

  if (loading) return <div className="p-6">Loading dashboard...</div>;

  return (
    <div className="flex">
      <Sidebar title="Student" items={tabs} active={active} onSelect={setActive} />
      <main className="flex-1 p-6 space-y-6">
        <div className="flex justify-end">
          <button onClick={onLogout} className="bg-slate-800 text-white px-4 py-2 rounded">
            Log out
          </button>
        </div>
        {active === "Assignments" && (
          <>
            <h1 className="text-2xl font-bold">All Assignments</h1>
            <div className="grid gap-3">
              {assignments.map((a) => (
                <div key={a.id} className="bg-white rounded shadow p-4">
                  <h2 className="font-semibold">{a.title}</h2>
                  <p className="text-slate-600">{a.description}</p>
                  <p className="text-sm text-slate-500 mt-1">
                    Due: {a.due_date ? new Date(a.due_date).toLocaleString() : "No due date"}
                  </p>
                  <p className="text-sm text-slate-500">
                    Multiple submissions: {a.allow_multiple_submissions ? "Allowed (best score kept)" : "Not allowed"}
                  </p>
                </div>
              ))}
            </div>
            <form onSubmit={onSubmit} className="bg-white rounded shadow p-4 space-y-3">
              <h2 className="font-semibold">Submit Assignment</h2>
              <select className="w-full border p-2 rounded" value={submissionState.assignment_id} onChange={(e) => setSubmissionState({ ...submissionState, assignment_id: e.target.value })} required>
                <option value="">Select assignment</option>
                {assignments.map((a) => (
                  <option key={a.id} value={a.id}>{a.title}</option>
                ))}
              </select>
              <textarea className="w-full border p-2 rounded" placeholder="Paste answer text" value={submissionState.text} onChange={(e) => setSubmissionState({ ...submissionState, text: e.target.value })} rows={4} />
              <input
                className="w-full border p-2 rounded"
                type="file"
                accept=".png,.jpg,.jpeg,.pdf,.txt"
                onChange={(e) => setSubmissionState({ ...submissionState, file: e.target.files?.[0] || null })}
              />
              {error && <p className="text-sm text-red-600">{error}</p>}
              <button
                className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
                disabled={
                  submitting ||
                  (() => {
                    const selected = assignments.find((item) => String(item.id) === String(submissionState.assignment_id));
                    return Boolean(selected && isPastDue(selected.due_date));
                  })()
                }
              >
                {submitting ? "Submitting..." : "Submit"}
              </button>
            </form>
            {submissionState.assignment_id && (() => {
              const selected = assignments.find((item) => String(item.id) === String(submissionState.assignment_id));
              if (!selected || !isPastDue(selected.due_date)) return null;
              return <p className="text-sm text-red-600">Selected assignment is past due and cannot be submitted.</p>;
            })()}
          </>
        )}

        {active === "My Results" && (
          <>
            <h1 className="text-2xl font-bold">My Results</h1>
            <div className="grid gap-3">
              {results.map((result) => (
                <div key={result.id} className="bg-white rounded shadow p-4">
                  <p><strong>Assignment:</strong> {result.assignment_title}</p>
                  <p><strong>Score:</strong> {result.score}</p>
                  <p><strong>Grade:</strong> {result.grade}</p>
                </div>
              ))}
              {results.length === 0 && <p className="text-slate-600">No results published yet.</p>}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
