"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "../../components/Sidebar";
import EvaluationBreakdown from "../../components/EvaluationBreakdown";
import {
  deleteMySubmissionsForAssignment,
  getAssignments,
  getMe,
  getMySubmissions,
  getStudentResults,
  logout,
  submitAssignment,
  submissionFileUrl
} from "../../lib/api";

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
  const [mySubmissions, setMySubmissions] = useState([]);
  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState("");
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState(null);
  const [pollingSubmissionId, setPollingSubmissionId] = useState(null);

  const isPastDue = (dueDate) => {
    if (!dueDate) return false;
    return new Date(dueDate).getTime() < Date.now();
  };

  const load = async (options = { showSpinner: true }) => {
    if (options.showSpinner) setLoading(true);
    try {
      const me = await getMe();
      if (me.data.role !== "student") {
        router.replace("/teacher");
        return;
      }
      const [assignmentRes, resultRes, mineRes] = await Promise.all([
        getAssignments(),
        getStudentResults({ eachSubmission: true }),
        getMySubmissions()
      ]);
      setAssignments(assignmentRes.data);
      setResults(resultRes.data);
      setMySubmissions(mineRes.data);
    } catch {
      router.replace("/login");
    } finally {
      if (options.showSpinner) setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!pollingSubmissionId) return undefined;
    const t = setInterval(async () => {
      try {
        const { data } = await getMySubmissions();
        setMySubmissions(data);
        const s = data.find((row) => row.id === pollingSubmissionId);
        if (s?.grading_complete) {
          setPollingSubmissionId(null);
          const [ar, rr] = await Promise.all([
            getAssignments(),
            getStudentResults({ eachSubmission: true })
          ]);
          setAssignments(ar.data);
          setResults(rr.data);
        }
      } catch {
        // ignore poll errors
      }
    }, 1500);
    return () => clearInterval(t);
  }, [pollingSubmissionId]);

  useEffect(() => {
    const f = submissionState.file;
    if (!f) {
      setPdfPreviewUrl(null);
      return undefined;
    }
    const isPdf = f.type === "application/pdf" || (f.name && f.name.toLowerCase().endsWith(".pdf"));
    if (!isPdf) {
      setPdfPreviewUrl(null);
      return undefined;
    }
    const u = URL.createObjectURL(f);
    setPdfPreviewUrl(u);
    return () => {
      URL.revokeObjectURL(u);
    };
  }, [submissionState.file]);

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
      const { data: newSub } = await submitAssignment({
        assignmentId: Number(submissionState.assignment_id),
        text: submissionState.text?.trim() || "",
        file: submissionState.file
      });
      setSubmissionState({ assignment_id: "", text: "", file: null });
      if (newSub && newSub.grading_complete === false) {
        setPollingSubmissionId(newSub.id);
      }
      await load({ showSpinner: false });
    } catch (err) {
      setError(err.response?.data?.detail || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  const assignmentIdsWithSubmission = new Set(mySubmissions.map((s) => s.assignment_id));

  const onDeleteSubmission = async (assignment) => {
    if (!window.confirm(`Remove your submission for “${assignment.title}”? This cannot be undone.`)) {
      return;
    }
    setDeleteError("");
    setDeletingId(assignment.id);
    try {
      await deleteMySubmissionsForAssignment(assignment.id);
      await load();
    } catch (err) {
      setDeleteError(err.response?.data?.detail || "Could not delete submission");
    } finally {
      setDeletingId(null);
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
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <h2 className="font-semibold">{a.title}</h2>
                    {assignmentIdsWithSubmission.has(a.id) && !isPastDue(a.due_date) && (
                      <button
                        type="button"
                        className="shrink-0 text-sm rounded border border-red-300 bg-red-50 px-3 py-1.5 text-red-800 hover:bg-red-100 disabled:opacity-50"
                        disabled={deletingId === a.id}
                        onClick={() => onDeleteSubmission(a)}
                      >
                        {deletingId === a.id ? "Deleting…" : "Delete my submission"}
                      </button>
                    )}
                  </div>
                  <p className="text-slate-600">{a.description}</p>
                  <p className="text-sm text-slate-500 mt-1">
                    Due: {a.due_date ? new Date(a.due_date).toLocaleString() : "No due date"}
                  </p>
                  <p className="text-sm text-slate-500">
                    Multiple submissions: {a.allow_multiple_submissions ? "Allowed (best score kept)" : "Not allowed"}
                  </p>
                  {assignmentIdsWithSubmission.has(a.id) && isPastDue(a.due_date) && (
                    <p className="text-xs text-slate-500 mt-2">Submission is locked after the due date; deletion is not available.</p>
                  )}
                  {mySubmissions
                    .filter((s) => s.assignment_id === a.id)
                    .map((s) => (
                      <div key={s.id} className="mt-3 pt-2 border-t border-slate-100 text-sm text-slate-600">
                        <p>
                          Submission #{s.id}
                          {s.submitted_at
                            ? ` · ${new Date(s.submitted_at).toLocaleString()}`
                            : ""}
                        </p>
                        {s.file_path ? (
                          <a
                            href={submissionFileUrl(s.id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-600 hover:underline font-medium"
                          >
                            View your submitted file
                          </a>
                        ) : (
                          <span className="text-slate-500">(text only)</span>
                        )}
                        <p className="mt-1.5 text-slate-800">
                          {s.grading_complete ? (
                            <>
                              <strong>Score:</strong> {s.result_score ?? "—"} · <strong>Grade:</strong>{" "}
                              {s.result_grade ?? "—"}
                            </>
                          ) : (
                            <span className="text-amber-800">
                              <strong>Grading in progress</strong> — this usually takes a few seconds. This page
                              updates automatically.
                            </span>
                          )}
                        </p>
                      </div>
                    ))}
                </div>
              ))}
            </div>
            {deleteError && <p className="text-sm text-red-600">{deleteError}</p>}
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
                accept=".png,.jpg,.jpeg,.pdf,.txt,.tif,.tiff,.webp,.bmp"
                onChange={(e) => setSubmissionState({ ...submissionState, file: e.target.files?.[0] || null })}
              />
              {pdfPreviewUrl && (
                <div className="border border-slate-200 rounded overflow-hidden bg-slate-50">
                  <p className="text-xs text-slate-500 px-2 py-1 bg-slate-100">Preview (before you submit)</p>
                  <object
                    data={pdfPreviewUrl}
                    type="application/pdf"
                    className="w-full h-[min(60vh,520px)]"
                    title="PDF preview"
                  />
                </div>
              )}
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
                  <p>
                    <strong>Submission #:</strong> {result.submission_id}
                  </p>
                  {result.submitted_at && (
                    <p>
                      <strong>Submitted:</strong> {new Date(result.submitted_at).toLocaleString()}
                    </p>
                  )}
                  {result.has_submission_file && (
                    <p>
                      <a
                        href={submissionFileUrl(result.submission_id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-600 hover:underline font-medium"
                      >
                        View your submitted file
                      </a>
                    </p>
                  )}
                  <p>
                    <strong>Score:</strong>{" "}
                    {result.score}
                    {result.feedback?.final_evaluation?.max_marks != null
                      ? ` / ${result.feedback.final_evaluation.max_marks}`
                      : " / 10"}
                  </p>
                  <p><strong>Grade:</strong> {result.grade}</p>
                  <EvaluationBreakdown result={result} />
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
