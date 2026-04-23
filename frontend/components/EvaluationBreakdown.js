"use client";

import { useMemo, useState } from "react";
import { gradeBandsDescription, gradeFromNormalizedScore } from "../lib/grading";

function formatMetricLabel(key) {
  return key
    .replace(/_contribution$/i, "")
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function num(v, digits = 4) {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

export default function EvaluationBreakdown({ result }) {
  const [showRaw, setShowRaw] = useState(false);

  const payload = useMemo(() => {
    const feedback = result?.feedback || {};
    const incomplete = Boolean(feedback._evaluation_incomplete);
    const stages = feedback.stages || {};
    const finalEval = feedback.final_evaluation || {};
    const nlp = stages.nlp_analysis || {};
    const deep = stages.deep_analysis || {};
    const ocr = stages.ocr_output || {};
    const breakdown = finalEval.weighted_breakdown || stages.adaptive_scoring?.weighted_contributions || {};
    const maxMarks = finalEval.max_marks ?? 10;
    const extracted =
      result?.ocr_extracted_text ||
      (typeof ocr.extracted_text === "string" ? ocr.extracted_text : "") ||
      "";

    return {
      feedback,
      incomplete,
      incompleteMessage: feedback.message,
      finalEval,
      nlp,
      deep,
      ocr,
      breakdown,
      maxMarks,
      extracted
    };
  }, [result]);

  const { finalEval, nlp, deep, breakdown, maxMarks, extracted, feedback, incomplete, incompleteMessage } = payload;
  const marks = finalEval.marks_obtained ?? result?.score;
  const storedGrade = finalEval.grade ?? result?.grade;
  const normalizedFromEval = finalEval.final_score_0_1;
  const normalizedFallback =
    normalizedFromEval !== undefined && normalizedFromEval !== null
      ? Number(normalizedFromEval)
      : maxMarks > 0
        ? Number(marks) / maxMarks
        : null;
  const gradeComputed = gradeFromNormalizedScore(normalizedFallback);
  const grade = gradeComputed ?? storedGrade;
  const normalized = normalizedFallback;
  const rougeFusion = Math.max(Number(nlp.rouge_1_recall) || 0, Number(nlp.rouge_l_recall) || 0);

  const rawMetricRows = [
    { label: "Keyword coverage", value: nlp.keyword_score },
    { label: "BLEU (surface)", value: nlp.bleu_score },
    { label: "ROUGE-1 recall", value: nlp.rouge_1_recall },
    { label: "ROUGE-L recall", value: nlp.rouge_l_recall },
    { label: "ROUGE used in fusion (max of above)", value: rougeFusion },
    { label: "Semantic similarity", value: nlp.semantic_similarity_score },
    { label: "Relevance / completeness", value: nlp.relevance_completeness_score },
    { label: "Structure quality", value: nlp.structure_score },
    { label: "Length normalization", value: nlp.length_normalization_score },
    { label: "Concept coverage (deep)", value: deep.concept_coverage_score }
  ];

  const contributionEntries = Object.entries(breakdown).sort(([a], [b]) => a.localeCompare(b));

  if (!result) {
    return null;
  }

  return (
    <div className="mt-4 space-y-4 border-t border-slate-200 pt-4">
      <h3 className="text-sm font-semibold text-slate-800">Assignment evaluation</h3>

      {incomplete && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
          <p className="font-medium">Limited detail on this result</p>
          <p className="mt-1">{incompleteMessage || "Full metrics and OCR text are not stored for this row."}</p>
          <p className="mt-1 text-xs text-amber-900/90">
            Ask your teacher to open Submissions and run <strong>Evaluate</strong> again (force) so the system saves the
            complete report.
          </p>
        </div>
      )}

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
        <p>
          <span className="text-slate-600">Marks: </span>
          <strong>
            {num(marks, 2)} / {maxMarks}
          </strong>
        </p>
        <p>
          <span className="text-slate-600">Grade: </span>
          <strong>{grade ?? "—"}</strong>
          {storedGrade && grade && storedGrade !== grade ? (
            <span className="ml-2 text-xs text-amber-700">(stored letter: {storedGrade}; shown from score bands)</span>
          ) : null}
        </p>
        {normalized !== undefined && normalized !== null && !Number.isNaN(normalized) && (
          <p>
            <span className="text-slate-600">Normalized score: </span>
            <strong>{num(normalized, 4)}</strong>
            <span className="text-slate-500"> ({num(normalized * 100, 2)}%)</span>
          </p>
        )}
        <p className="mt-1 text-xs text-slate-500">{gradeBandsDescription()}</p>
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Scoring inputs (0–1)</h4>
        <div className="overflow-x-auto rounded border border-slate-200">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-100 text-slate-700">
              <tr>
                <th className="px-3 py-2 font-medium">Metric</th>
                <th className="px-3 py-2 font-medium">Value</th>
              </tr>
            </thead>
            <tbody>
              {rawMetricRows.map((row) => (
                <tr key={row.label} className="border-t border-slate-100">
                  <td className="px-3 py-2 text-slate-700">{row.label}</td>
                  <td className="px-3 py-2 font-mono text-slate-900">{num(row.value, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {contributionEntries.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Weighted contributions to final score
          </h4>
          <div className="overflow-x-auto rounded border border-slate-200">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-100 text-slate-700">
                <tr>
                  <th className="px-3 py-2 font-medium">Component</th>
                  <th className="px-3 py-2 font-medium">Contribution</th>
                </tr>
              </thead>
              <tbody>
                {contributionEntries.map(([key, value]) => (
                  <tr key={key} className="border-t border-slate-100">
                    <td className="px-3 py-2 text-slate-700">{formatMetricLabel(key)}</td>
                    <td className="px-3 py-2 font-mono text-slate-900">{num(value, 4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Extracted text</h4>
        {extracted ? (
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded border border-amber-200 bg-amber-50 p-3 text-xs text-slate-800">
            {extracted}
          </pre>
        ) : (
          <p className="text-sm text-slate-500">No extracted text in this result payload.</p>
        )}
      </div>

      <div>
        <button
          type="button"
          className="text-xs text-slate-600 underline decoration-slate-400 hover:text-slate-900"
          onClick={() => setShowRaw((s) => !s)}
        >
          {showRaw ? "Hide raw ML JSON" : "Show raw ML JSON"}
        </button>
        {showRaw && (
          <pre className="mt-2 max-h-96 overflow-auto rounded bg-slate-100 p-3 text-xs">{JSON.stringify(feedback, null, 2)}</pre>
        )}
      </div>
    </div>
  );
}
