/** Mirrors ml/config.py PipelineConfig.score_grades (threshold on 0–1 scale, highest first). */
const SCORE_GRADE_BANDS = [
  [0.85, "A"],
  [0.7, "B"],
  [0.55, "C"],
  [0.0, "D"]
];

export function gradeFromNormalizedScore(final01) {
  const n = Number(final01);
  if (final01 === null || final01 === undefined || Number.isNaN(n)) return null;
  for (const [threshold, label] of SCORE_GRADE_BANDS) {
    if (n >= threshold) return label;
  }
  return "D";
}

export function gradeBandsDescription() {
  return "A ≥ 85%, B ≥ 70%, C ≥ 55%, D otherwise (from normalized score 0–1).";
}
