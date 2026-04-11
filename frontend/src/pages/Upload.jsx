import { useEffect, useState, useRef } from "react";
import { api } from "../api/client.js";
import FileDropzone from "../components/FileDropzone.jsx";

export default function Upload() {
  const [assignments, setAssignments] = useState([]);
  const [assignmentId, setAssignmentId] = useState("");
  const [lang, setLang] = useState("en");
  const [status, setStatus] = useState("");
  const [lastId, setLastId] = useState(() => localStorage.getItem("lastSubmissionId") || "");
  const wsLog = useRef([]);

  useEffect(() => {
    api
      .assignments()
      .then(setAssignments)
      .catch(() => setAssignments([]));
  }, []);

  useEffect(() => {
    if (!assignmentId && assignments.length) setAssignmentId(String(assignments[0].id));
  }, [assignments, assignmentId]);

  async function uploadOne(file) {
    if (!assignmentId) {
      setStatus("Select an assignment.");
      return;
    }
    setStatus("Uploading…");
    const jobId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
    const apiBase = import.meta.env.VITE_API_URL || "";
    let wsUrl;
    if (apiBase) {
      const u = new URL(apiBase);
      const wsProto = u.protocol === "https:" ? "wss:" : "ws:";
      wsUrl = `${wsProto}//${u.host}/api/v1/submissions/ws/${jobId}`;
    } else {
      const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
      wsUrl = `${wsProto}//${window.location.host}/api/v1/submissions/ws/${jobId}`;
    }
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (ev) => {
      wsLog.current.push(ev.data);
      setStatus(`WS: ${ev.data}`);
    };

    const fd = new FormData();
    fd.set("assignment_id", assignmentId);
    fd.set("language_hint", lang);
    fd.set("job_id", jobId);
    fd.set("file", file);
    try {
      const sub = await api.upload(fd);
      localStorage.setItem("lastSubmissionId", String(sub.id));
      setLastId(String(sub.id));
      setStatus(`Uploaded submission #${sub.id}. Go to Results to evaluate.`);
    } catch (e) {
      setStatus(e.message || "Upload failed");
    } finally {
      ws.close();
    }
  }

  async function batchUpload(files) {
    if (!assignmentId) return;
    setStatus("Batch uploading…");
    const fd = new FormData();
    fd.set("assignment_id", assignmentId);
    fd.set("language_hint", lang);
    files.forEach((f) => fd.append("files", f));
    try {
      const subs = await api.batchUpload(fd);
      setStatus(`Uploaded ${subs.length} submissions. Last id: ${subs[subs.length - 1]?.id}`);
    } catch (e) {
      setStatus(e.message || "Batch failed");
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-ink-950">Upload answer sheet</h1>
        <p className="text-slate-600 mt-1">PNG, JPG, or PDF. Hindi scans: set language hint to Hindi.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4">
          <label className="block text-sm font-medium text-slate-700">Assignment</label>
          <select
            className="w-full border border-slate-300 rounded-lg px-3 py-2"
            value={assignmentId}
            onChange={(e) => setAssignmentId(e.target.value)}
          >
            {assignments.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title} (#{a.id})
              </option>
            ))}
          </select>
          <label className="block text-sm font-medium text-slate-700">OCR language hint</label>
          <select
            className="w-full border border-slate-300 rounded-lg px-3 py-2"
            value={lang}
            onChange={(e) => setLang(e.target.value)}
          >
            <option value="en">English</option>
            <option value="hi">Hindi + English (Tesseract)</option>
          </select>
          {lastId && (
            <p className="text-sm text-slate-500">
              Last submission id: <strong>{lastId}</strong> (stored locally)
            </p>
          )}
        </div>
        <div className="space-y-4">
          <FileDropzone onFiles={(files) => uploadOne(files[0])} />
          <FileDropzone multiple onFiles={batchUpload} />
          <p className="text-xs text-slate-500 text-center">Second drop zone: batch multi-file upload</p>
        </div>
      </div>

      {status && (
        <div className="rounded-xl bg-slate-900 text-slate-100 px-4 py-3 font-mono text-sm whitespace-pre-wrap">
          {status}
        </div>
      )}
    </div>
  );
}
