import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import ScoreChart from "../components/ScoreChart.jsx";

export default function Results() {
  const [submissionId, setSubmissionId] = useState(() => localStorage.getItem("lastSubmissionId") || "");
  const [assignments, setAssignments] = useState([]);
  const [modelAnswerId, setModelAnswerId] = useState("");
  const [sub, setSub] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [assignmentDetail, setAssignmentDetail] = useState(null);

  useEffect(() => {
    api.assignments().then(setAssignments).catch(() => {});
  }, []);

  useEffect(() => {
    if (!sub?.assignment_id) return;
    const fromList = assignments.find((a) => a.id === sub.assignment_id);
    if (fromList?.model_answers?.length) {
      setAssignmentDetail(fromList);
      return;
    }
    api
      .assignment(sub.assignment_id)
      .then(setAssignmentDetail)
      .catch(() => setAssignmentDetail(null));
  }, [sub, assignments]);

  async function load() {
    if (!submissionId) return;
    setLoading(true);
    setErr("");
    try {
      const s = await api.getSubmission(submissionId);
      setSub(s);
    } catch (e) {
      setErr(e.message);
      setSub(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runEval() {
    if (!submissionId || !modelAnswerId) return;
    setLoading(true);
    setErr("");
    try {
      const s = await api.evaluate(submissionId, {
        model_answer_id: Number(modelAnswerId),
        run_plagiarism: true,
      });
      setSub(s);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  const assignment = assignmentDetail || assignments.find((a) => a.id === sub?.assignment_id);
  const models = assignment?.model_answers || [];

  useEffect(() => {
    if (models.length && !modelAnswerId) setModelAnswerId(String(models[0].id));
  }, [models, modelAnswerId]);

  const primaryScore = sub?.scores?.[0];

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-ink-950">Results</h1>

      <div className="flex flex-wrap gap-3 items-end bg-white border border-slate-200 rounded-2xl p-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Submission ID</label>
          <input
            className="border border-slate-300 rounded-lg px-3 py-2 w-40"
            value={submissionId}
            onChange={(e) => setSubmissionId(e.target.value)}
          />
        </div>
        <button type="button" onClick={load} className="px-4 py-2 bg-slate-800 text-white rounded-lg text-sm">
          Load
        </button>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Model answer</label>
          <select
            className="border border-slate-300 rounded-lg px-3 py-2 min-w-[200px]"
            value={modelAnswerId}
            onChange={(e) => setModelAnswerId(e.target.value)}
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.question_key}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={runEval}
          disabled={loading}
          className="px-4 py-2 bg-accent text-white rounded-lg text-sm disabled:opacity-50"
        >
          Run evaluation
        </button>
      </div>

      {err && <p className="text-red-600 text-sm">{err}</p>}
      {loading && <p className="text-slate-500">Loading…</p>}

      {sub && (
        <div className="grid lg:grid-cols-2 gap-8">
          <div className="bg-white border border-slate-200 rounded-2xl p-6">
            <h2 className="font-semibold text-lg mb-2">Extracted text</h2>
            <pre className="text-sm bg-slate-50 border border-slate-100 rounded-xl p-4 max-h-80 overflow-auto whitespace-pre-wrap">
              {sub.extracted_text || "—"}
            </pre>
            <p className="text-xs text-slate-500 mt-2">Status: {sub.status}</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4">
            <h2 className="font-semibold text-lg">Scores</h2>
            {primaryScore ? (
              <>
                <div className="flex gap-6 flex-wrap">
                  <div>
                    <p className="text-sm text-slate-500">Final</p>
                    <p className="text-3xl font-bold text-ink-950">{primaryScore.final_score ?? primaryScore.auto_score}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Auto</p>
                    <p className="text-xl font-semibold">{primaryScore.auto_score}</p>
                  </div>
                </div>
                <ScoreChart
                  semantic={primaryScore.semantic_similarity}
                  keyword={primaryScore.keyword_score}
                  maxScore={assignment?.max_score ? Number(assignment.max_score) : 100}
                />
                {primaryScore.explainability && (
                  <div className="text-sm text-slate-700 space-y-2 border-t border-slate-100 pt-4">
                    <p className="font-medium text-ink-950">Why this score</p>
                    <p>{primaryScore.explainability.rationale}</p>
                    {primaryScore.explainability.matched_keywords?.length > 0 && (
                      <p>
                        <span className="text-green-700 font-medium">Matched: </span>
                        {primaryScore.explainability.matched_keywords.join(", ")}
                      </p>
                    )}
                    {primaryScore.explainability.missing_keywords?.length > 0 && (
                      <p>
                        <span className="text-amber-700 font-medium">Missing: </span>
                        {primaryScore.explainability.missing_keywords.join(", ")}
                      </p>
                    )}
                  </div>
                )}
              </>
            ) : (
              <p className="text-slate-500">Run evaluation to compute scores.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
