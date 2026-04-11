"""
Weighted scoring (semantic + keywords), explainability, and structured feedback.

Optional plagiarism penalty applied upstream as a scalar in [0,1].
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from app.config import get_settings
from app.models.orm import ModelAnswer
from app.schemas.submission import Explainability
from app.services import nlp_service


def _weights() -> tuple[float, float]:
    s = get_settings()
    ws, wk = float(s.weight_semantic), float(s.weight_keyword)
    total = ws + wk or 1.0
    return ws / total, wk / total


def build_keyword_lists(model: ModelAnswer, student_text: str) -> tuple[list[str], list[str]]:
    ref_kws: list[str] = []
    if model.keywords_json and isinstance(model.keywords_json, dict):
        raw = model.keywords_json.get("keywords") or model.keywords_json.get("items")
        if isinstance(raw, list):
            ref_kws = [str(x) for x in raw]
    if not ref_kws:
        ref_kws = nlp_service.extract_keywords_keybert(model.reference_text)
    stud_kws = nlp_service.extract_keywords_keybert(student_text)
    return stud_kws, ref_kws


def compute_scores(
    student_text: str,
    model: ModelAnswer,
    max_score: Decimal,
    plagiarism_similarity: Optional[float] = None,
) -> tuple[Decimal, float, float, Explainability]:
    """
    Returns auto_score, semantic_sim, keyword_score, explainability.
    """
    ws, wk = _weights()
    sem = nlp_service.semantic_similarity(student_text, model.reference_text)
    stud_kws, ref_kws = build_keyword_lists(model, student_text)
    k_score = nlp_service.keyword_overlap_score(stud_kws, ref_kws)

    plag_penalty = 0.0
    if plagiarism_similarity is not None and plagiarism_similarity > 0.85:
        plag_penalty = min(0.35, (plagiarism_similarity - 0.85) * 2.0)

    combined = ws * sem + wk * k_score
    combined_after = max(0.0, combined * (1.0 - plag_penalty))
    auto = Decimal(str(round(float(max_score) * combined_after, 2)))

    matched = sorted(set(stud_kws) & set(ref_kws), key=lambda x: -len(x))[:20]
    missing = sorted(set(ref_kws) - set(stud_kws), key=lambda x: -len(x))[:20]

    rationale_parts = [
        f"Semantic alignment contributes {sem:.2f} (weight {ws:.2f}).",
        f"Keyword overlap contributes {k_score:.2f} (weight {wk:.2f}).",
    ]
    if plag_penalty > 0:
        rationale_parts.append(
            f"Plagiarism-like similarity reduced the score by ~{plag_penalty*100:.1f}%."
        )
    rationale = " ".join(rationale_parts)

    explain = Explainability(
        semantic_component=float(sem * ws),
        keyword_component=float(k_score * wk),
        plagiarism_penalty=plag_penalty,
        matched_keywords=matched,
        missing_keywords=missing,
        rationale=rationale,
    )
    return auto, sem, k_score, explain


def attention_highlights(student_text: str, missing_keywords: list[str]) -> list[dict[str, Any]]:
    """
    Lightweight 'attention' proxy: flag sentences with few overlapping important terms.

    Not transformer attention maps—practical UI highlights for weak regions.
    """
    sentences = [s.strip() for s in student_text.replace("?", ".").split(".") if s.strip()]
    out: list[dict[str, Any]] = []
    miss_set = {m.lower() for m in missing_keywords}
    for sent in sentences[:30]:
        low = sent.lower()
        overlap = sum(1 for m in miss_set if m and m in low)
        if overlap == 0 and len(sent) > 40:
            out.append({"sentence": sent, "reason": "low_keyword_overlap"})
    return out[:8]


def build_feedback(
    student_text: str,
    reference_text: str,
    explain: Explainability,
    semantic: float,
    keyword_score: float,
) -> dict[str, Any]:
    """Structured feedback for persistence and API."""
    missing_concepts = explain.missing_keywords[:12]
    weak_areas: list[str] = []
    if semantic < 0.45:
        weak_areas.append("Overall explanation diverges from the reference answer.")
    if keyword_score < 0.35:
        weak_areas.append("Key terms from the model solution are underrepresented.")

    suggestions: list[str] = []
    if missing_concepts:
        suggestions.append(f"Review and define: {', '.join(missing_concepts[:5])}.")
    if semantic < 0.55:
        suggestions.append("Add a concise cause-effect chain linking concepts to the question.")
    if not suggestions:
        suggestions.append("Refine clarity with a short summary sentence and one concrete example.")

    summary = explain.rationale
    if weak_areas:
        summary += " " + " ".join(weak_areas)

    highlights = attention_highlights(student_text, missing_concepts)

    return {
        "summary": summary,
        "missing_concepts": missing_concepts,
        "weak_areas": weak_areas,
        "suggestions": suggestions,
        "attention_highlights": highlights,
    }
