from __future__ import annotations

from dataclasses import dataclass

from ml.config import PipelineConfig


@dataclass
class ScoringResult:
    final_score_0_1: float
    marks_obtained: float
    grade: str
    weighted_breakdown: dict[str, float]


def compute_final_score(
    keyword_score: float,
    semantic_score: float,
    grammar_score: float,
    relevance_score: float,
    concept_coverage: float,
    coherence_score: float,
    config: PipelineConfig,
) -> ScoringResult:
    w = config.scoring_weights.normalized()
    final = (
        w.w1_keyword * keyword_score
        + w.w2_semantic * semantic_score
        + w.w3_grammar * grammar_score
        + w.w4_relevance * relevance_score
        + w.w5_concept_coverage * concept_coverage
        + w.w6_coherence * coherence_score
    )
    final = max(0.0, min(1.0, final))
    marks = round(final * config.max_marks, 2)
    grade = "D"
    for threshold, grade_label in config.score_grades:
        if final >= threshold:
            grade = grade_label
            break
    breakdown = {
        "w1_keyword": round(w.w1_keyword * keyword_score, 4),
        "w2_semantic": round(w.w2_semantic * semantic_score, 4),
        "w3_grammar": round(w.w3_grammar * grammar_score, 4),
        "w4_relevance": round(w.w4_relevance * relevance_score, 4),
        "w5_concept_coverage": round(w.w5_concept_coverage * concept_coverage, 4),
        "w6_coherence": round(w.w6_coherence * coherence_score, 4),
    }
    return ScoringResult(final_score_0_1=final, marks_obtained=marks, grade=grade, weighted_breakdown=breakdown)

