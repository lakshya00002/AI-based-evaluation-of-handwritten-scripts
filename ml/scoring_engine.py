from __future__ import annotations

from dataclasses import dataclass

from ml.config import PipelineConfig


@dataclass
class ScoringResult:
    final_score_0_1: float
    marks_obtained: float
    max_marks: int
    grade: str
    weighted_breakdown: dict[str, float]


def _grade_from_thresholds(final_0_1: float, score_grades: tuple[tuple[float, str], ...]) -> str:
    """Pick the letter grade for the highest band whose threshold `final_0_1` meets or exceeds."""
    if not score_grades:
        return "D"
    for threshold, label in sorted(score_grades, key=lambda item: item[0], reverse=True):
        if final_0_1 >= threshold:
            return label
    return score_grades[-1][1]


def compute_final_score(
    keyword_coverage_score: float,
    bleu_score: float,
    rouge_score: float,
    semantic_score: float,
    relevance_score: float,
    concept_coverage: float,
    structure_score: float,
    length_normalization_score: float,
    config: PipelineConfig,
) -> ScoringResult:
    w = config.scoring_weights.normalized()
    final = (
        w.w1_keyword_coverage * keyword_coverage_score
        + w.w2_bleu_surface * bleu_score
        + w.w3_rouge_recall * rouge_score
        + w.w4_semantic_correctness * semantic_score
        + w.w5_concept_coverage * concept_coverage
        + w.w6_structure_quality * structure_score
        + w.w7_relevance * relevance_score
        + w.w8_length_normalization * length_normalization_score
    )
    final = max(0.0, min(1.0, final))
    marks = round(final * config.max_marks, 2)
    grade = _grade_from_thresholds(final, config.score_grades)
    breakdown = {
        "keyword_coverage_contribution": round(w.w1_keyword_coverage * keyword_coverage_score, 4),
        "bleu_surface_contribution": round(w.w2_bleu_surface * bleu_score, 4),
        "rouge_recall_contribution": round(w.w3_rouge_recall * rouge_score, 4),
        "semantic_correctness_contribution": round(w.w4_semantic_correctness * semantic_score, 4),
        "concept_coverage_contribution": round(w.w5_concept_coverage * concept_coverage, 4),
        "structure_quality_contribution": round(w.w6_structure_quality * structure_score, 4),
        "relevance_contribution": round(w.w7_relevance * relevance_score, 4),
        "length_normalization_contribution": round(w.w8_length_normalization * length_normalization_score, 4),
    }
    return ScoringResult(
        final_score_0_1=final,
        marks_obtained=marks,
        max_marks=config.max_marks,
        grade=grade,
        weighted_breakdown=breakdown,
    )

