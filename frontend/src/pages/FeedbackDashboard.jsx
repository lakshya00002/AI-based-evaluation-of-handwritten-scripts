import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function FeedbackDashboard() {
  const [submissionId, setSubmissionId] = useState(() => localStorage.getItem("lastSubmissionId") || "");
  const [sub, setSub] = useState(null);

  async function load() {
    if (!submissionId) return;
    const s = await api.getSubmission(submissionId);
    setSub(s);
  }

  useEffect(() => {
    load().catch(() => setSub(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fb = sub?.scores?.[0]?.feedback;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-ink-950">Feedback dashboard</h1>
      <div className="flex gap-3 items-end">
        <input
          className="border border-slate-300 rounded-lg px-3 py-2 w-40"
          value={submissionId}
          onChange={(e) => setSubmissionId(e.target.value)}
        />
        <button type="button" onClick={() => load().catch(() => {})} className="px-4 py-2 bg-accent text-white rounded-lg text-sm">
          Refresh
        </button>
      </div>

      {!fb && <p className="text-slate-500">No feedback yet—run evaluation on the Results page.</p>}

      {fb && (
        <div className="grid md:grid-cols-2 gap-6">
          <section className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
            <h2 className="font-semibold text-amber-900 mb-2">Weak areas</h2>
            <ul className="list-disc list-inside text-sm text-amber-950 space-y-1">
              {(fb.weak_areas || []).map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
            <h3 className="font-medium mt-4 text-amber-900">Missing concepts</h3>
            <div className="flex flex-wrap gap-2 mt-2">
              {(fb.missing_concepts || []).map((m, i) => (
                <span key={i} className="px-2 py-1 bg-white border border-amber-200 rounded-md text-xs">
                  {m}
                </span>
              ))}
            </div>
          </section>
          <section className="bg-white border border-slate-200 rounded-2xl p-6">
            <h2 className="font-semibold text-ink-950 mb-2">Suggestions</h2>
            <ul className="list-decimal list-inside text-sm text-slate-700 space-y-2">
              {(fb.suggestions || []).map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
            <h3 className="font-medium mt-6 text-ink-950">Highlight proxy (low keyword overlap)</h3>
            <ul className="mt-2 space-y-2 text-sm text-slate-600">
              {(fb.attention_highlights || []).map((h, i) => (
                <li key={i} className="border-l-4 border-red-300 pl-3">
                  {h.sentence}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
