from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScoringWeights:
    w1_keyword: float = 0.16
    w2_semantic: float = 0.22
    w3_grammar: float = 0.14
    w4_relevance: float = 0.16
    w5_concept_coverage: float = 0.20
    w6_coherence: float = 0.12

    def normalized(self) -> "ScoringWeights":
        total = (
            self.w1_keyword
            + self.w2_semantic
            + self.w3_grammar
            + self.w4_relevance
            + self.w5_concept_coverage
            + self.w6_coherence
        ) or 1.0
        return ScoringWeights(
            w1_keyword=self.w1_keyword / total,
            w2_semantic=self.w2_semantic / total,
            w3_grammar=self.w3_grammar / total,
            w4_relevance=self.w4_relevance / total,
            w5_concept_coverage=self.w5_concept_coverage / total,
            w6_coherence=self.w6_coherence / total,
        )


@dataclass
class PipelineConfig:
    max_marks: int = 10
    min_dpi: int = 300
    score_grades: tuple[tuple[float, str], ...] = (
        (0.85, "A"),
        (0.70, "B"),
        (0.55, "C"),
        (0.00, "D"),
    )
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)

