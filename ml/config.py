from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScoringWeights:
    w1_keyword_coverage: float = 0.12
    w2_bleu_surface: float = 0.10
    w3_rouge_recall: float = 0.12
    w4_semantic_correctness: float = 0.24
    w5_concept_coverage: float = 0.18
    w6_structure_quality: float = 0.12
    w7_relevance: float = 0.06
    w8_length_normalization: float = 0.06

    def normalized(self) -> "ScoringWeights":
        total = (
            self.w1_keyword_coverage
            + self.w2_bleu_surface
            + self.w3_rouge_recall
            + self.w4_semantic_correctness
            + self.w5_concept_coverage
            + self.w6_structure_quality
            + self.w7_relevance
            + self.w8_length_normalization
        ) or 1.0
        return ScoringWeights(
            w1_keyword_coverage=self.w1_keyword_coverage / total,
            w2_bleu_surface=self.w2_bleu_surface / total,
            w3_rouge_recall=self.w3_rouge_recall / total,
            w4_semantic_correctness=self.w4_semantic_correctness / total,
            w5_concept_coverage=self.w5_concept_coverage / total,
            w6_structure_quality=self.w6_structure_quality / total,
            w7_relevance=self.w7_relevance / total,
            w8_length_normalization=self.w8_length_normalization / total,
        )


@dataclass
class PipelineConfig:
    max_marks: int = 10
    min_dpi: int = 200
    score_grades: tuple[tuple[float, str], ...] = (
        (0.85, "A"),
        (0.70, "B"),
        (0.55, "C"),
        (0.00, "D"),
    )
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)

