import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function TeacherDashboard() {
  const [assignments, setAssignments] = useState([]);
  const [aid, setAid] = useState("");
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .assignments()
      .then((a) => {
        setAssignments(a);
        if (a.length) setAid(String(a[0].id));
      })
      .catch(() => {});
  }, []);

  async function loadSubs() {
    if (!aid) return;
    setErr("");
    try {
      const list = await api.teacherSubmissions(aid);
      setRows(list);
    } catch (e) {
      setErr(e.message || "Forbidden—need teacher role");
      setRows([]);
    }
  }

  async function override(scoreId) {
    const v = window.prompt("New final score?");
    if (v == null) return;
    const note = window.prompt("Optional note for audit trail") || undefined;
    try {
      await api.overrideScore(scoreId, { final_score: Number(v), note });
      await loadSubs();
    } catch (e) {
      alert(e.message);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-ink-950">Teacher dashboard</h1>
      <p className="text-slate-600 text-sm">Manual score override and cohort review.</p>

      <div className="flex gap-3 items-center flex-wrap">
        <select
          className="border border-slate-300 rounded-lg px-3 py-2"
          value={aid}
          onChange={(e) => setAid(e.target.value)}
        >
          {assignments.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title}
            </option>
          ))}
        </select>
        <button type="button" onClick={loadSubs} className="px-4 py-2 bg-slate-800 text-white rounded-lg text-sm">
          Load submissions
        </button>
      </div>
      {err && <p className="text-red-600 text-sm">{err}</p>}

      <div className="overflow-x-auto border border-slate-200 rounded-2xl bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="p-3">Sub #</th>
              <th className="p-3">Student</th>
              <th className="p-3">Status</th>
              <th className="p-3">Auto</th>
              <th className="p-3">Final</th>
              <th className="p-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const sc = r.scores?.[0];
              return (
                <tr key={r.id} className="border-t border-slate-100">
                  <td className="p-3">{r.id}</td>
                  <td className="p-3">{r.student_id}</td>
                  <td className="p-3">{r.status}</td>
                  <td className="p-3">{sc?.auto_score ?? "—"}</td>
                  <td className="p-3">{sc?.final_score ?? "—"}</td>
                  <td className="p-3">
                    {sc ? (
                      <button type="button" className="text-accent font-medium" onClick={() => override(sc.id)}>
                        Override
                      </button>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
