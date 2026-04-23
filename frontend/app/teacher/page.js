"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "../../components/Sidebar";
import EvaluationBreakdown from "../../components/EvaluationBreakdown";
import {
  createAssignment,
  evaluateSubmission,
  getAssignments,
  getMe,
  getSubmissions,
  getTeacherResults,
  logout
} from "../../lib/api";

const tabs = ["Create Assignment", "Submissions", "Results"];

export default function TeacherDashboard() {
  const router = useRouter();
  const [active, setActive] = useState("Create Assignment");
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState("");
  const [submissions, setSubmissions] = useState([]);
  const [results, setResults] = useState([]);
  const [resultsError, setResultsError] = useState("");
  const [loadingResults, setLoadingResults] = useState(false);
  const [loading, setLoading] = useState(true);
  const [evalBusy, setEvalBusy] = useState(null);
  const [evalNotice, setEvalNotice] = useState("");

  const [form, setForm] = useState({
    title: "",
    description: "",
    due_date: "",
    allow_multiple_submissions: false,
    reference_answer: "",
    reference_keywords: "",
    reference_concepts: ""
  });
  const selectedAssignment = useMemo(
    () => assignments.find((item) => String(item.id) === String(selectedAssignmentId)),
    [assignments, selectedAssignmentId]
  );

  const loadAssignments = async () => {
    const { data } = await getAssignments();
    setAssignments(data);
    if (!selectedAssignmentId && data.length > 0) {
      setSelectedAssignmentId(String(data[0].id));
    }
  };

  const bootstrap = async () => {
    setLoading(true);
    try {
      const me = await getMe();
      if (me.data.role !== "teacher") {
        router.replace("/student");
        return;
      }
      await loadAssignments();
    } catch {
      router.replace("/login");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    bootstrap();
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      if (!selectedAssignmentId) return;
      if (active === "Submissions") {
        const { data } = await getSubmissions(selectedAssignmentId);
        setSubmissions(data);
      }
      if (active === "Results") {
        await fetchResults(selectedAssignmentId);
      }
    };
    fetchData();
  }, [active, selectedAssignmentId]);

  const fetchResults = async (assignmentId) => {
    setLoadingResults(true);
    setResultsError("");
    try {
      const { data } = await getTeacherResults(Number(assignmentId));
      setResults(data);
    } catch (err) {
      setResults([]);
      setResultsError(err.response?.data?.detail || "Unable to load results for this assignment");
    } finally {
      setLoadingResults(false);
    }
  };

  const runEvaluate = async (submissionId) => {
    setEvalBusy(submissionId);
    setEvalNotice("");
    try {
      await evaluateSubmission(submissionId, { force: true });
      setEvalNotice(`Submission #${submissionId} re-evaluated successfully.`);
      if (active === "Results" && selectedAssignmentId) {
        await fetchResults(selectedAssignmentId);
      }
    } catch (err) {
      setEvalNotice(err.response?.data?.detail || "Re-evaluation failed");
    } finally {
      setEvalBusy(null);
    }
  };

  const onCreate = async (e) => {
    e.preventDefault();
    await createAssignment({
      ...form,
      due_date: form.due_date ? new Date(form.due_date).toISOString() : null,
      reference_keywords: form.reference_keywords.split(",").map((v) => v.trim()).filter(Boolean),
      reference_concepts: form.reference_concepts.split(",").map((v) => v.trim()).filter(Boolean)
    });
    setForm({
      title: "",
      description: "",
      due_date: "",
      allow_multiple_submissions: false,
      reference_answer: "",
      reference_keywords: "",
      reference_concepts: ""
    });
    await loadAssignments();
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
      <Sidebar title="Teacher" items={tabs} active={active} onSelect={setActive} />
      <main className="flex-1 p-6 space-y-5">
        <div className="flex justify-end">
          <button onClick={onLogout} className="bg-slate-800 text-white px-4 py-2 rounded">
            Log out
          </button>
        </div>
        <div className="bg-white rounded p-4 shadow">
          <label className="text-sm">Assignment filter</label>
          <select className="border p-2 rounded w-full" value={selectedAssignmentId} onChange={(e) => setSelectedAssignmentId(e.target.value)}>
            <option value="">Select assignment</option>
            {assignments.map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}
          </select>
          {selectedAssignment && <p className="text-sm text-slate-600 mt-2">Current: {selectedAssignment.title}</p>}
        </div>

        {active === "Create Assignment" && (
          <form onSubmit={onCreate} className="bg-white rounded shadow p-4 space-y-3">
            <h1 className="text-2xl font-bold">Create Assignment</h1>
            <input className="w-full border p-2 rounded" placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            <textarea className="w-full border p-2 rounded" placeholder="Description" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required />
            <input className="w-full border p-2 rounded" type="datetime-local" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.allow_multiple_submissions} onChange={(e) => setForm({ ...form, allow_multiple_submissions: e.target.checked })} />
              Allow multiple submissions per student (best grade will be shown)
            </label>
            <textarea className="w-full border p-2 rounded" placeholder="Reference answer" rows={3} value={form.reference_answer} onChange={(e) => setForm({ ...form, reference_answer: e.target.value })} />
            <input className="w-full border p-2 rounded" placeholder="Reference keywords (comma separated)" value={form.reference_keywords} onChange={(e) => setForm({ ...form, reference_keywords: e.target.value })} />
            <input className="w-full border p-2 rounded" placeholder="Reference concepts (comma separated)" value={form.reference_concepts} onChange={(e) => setForm({ ...form, reference_concepts: e.target.value })} />
            <button className="bg-blue-600 text-white px-4 py-2 rounded">Create</button>
          </form>
        )}

        {active === "Submissions" && (
          <div className="space-y-3">
            <h1 className="text-2xl font-bold">Submissions for Assignment #{selectedAssignmentId}</h1>
            {evalNotice && (
              <p className={`text-sm ${evalNotice.includes("failed") ? "text-red-600" : "text-green-700"}`}>{evalNotice}</p>
            )}
            {submissions.map((submission) => (
              <div key={submission.id} className="bg-white rounded shadow p-4">
                <p><strong>Submission ID:</strong> {submission.id}</p>
                <p><strong>Student ID:</strong> {submission.student_id}</p>
                <p><strong>Text:</strong> {submission.text || "-"}</p>
                <p><strong>File path:</strong> {submission.file_path || "-"}</p>
                <p className="text-sm text-slate-500 mt-2">This submission is auto-evaluated at upload time.</p>
                <button
                  type="button"
                  className="mt-2 text-sm bg-indigo-600 text-white px-3 py-1.5 rounded disabled:opacity-50"
                  disabled={evalBusy === submission.id}
                  onClick={() => runEvaluate(submission.id)}
                >
                  {evalBusy === submission.id ? "Re-evaluating…" : "Re-run evaluation (refresh metrics & OCR)"}
                </button>
              </div>
            ))}
          </div>
        )}

        {active === "Results" && (
          <div className="space-y-3">
            <h1 className="text-2xl font-bold">Results for Assignment #{selectedAssignmentId}</h1>
            {loadingResults && <p className="text-slate-600">Loading results...</p>}
            {resultsError && <p className="text-red-600">{resultsError}</p>}
            {!loadingResults && !resultsError && results.length === 0 && (
              <p className="text-slate-600">No results yet for this assignment. Evaluate submissions first.</p>
            )}
            {evalNotice && active === "Results" && (
              <p className={`text-sm ${evalNotice.includes("failed") ? "text-red-600" : "text-green-700"}`}>{evalNotice}</p>
            )}
            {results.map((result) => (
              <div key={result.id} className="bg-white rounded shadow p-4">
                <p><strong>Assignment:</strong> {result.assignment_title}</p>
                <p><strong>Submission:</strong> #{result.submission_id}</p>
                <p><strong>Student ID:</strong> {result.student_id}</p>
                <p>
                  <strong>Score:</strong>{" "}
                  {result.score}
                  {result.feedback?.final_evaluation?.max_marks != null
                    ? ` / ${result.feedback.final_evaluation.max_marks}`
                    : " / 10"}
                </p>
                <p><strong>Grade:</strong> {result.grade}</p>
                <button
                  type="button"
                  className="mt-2 text-sm bg-indigo-600 text-white px-3 py-1.5 rounded disabled:opacity-50"
                  disabled={evalBusy === result.submission_id}
                  onClick={() => runEvaluate(result.submission_id)}
                >
                  {evalBusy === result.submission_id ? "Re-evaluating…" : "Re-run evaluation (refresh metrics & OCR)"}
                </button>
                <EvaluationBreakdown result={result} />
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
