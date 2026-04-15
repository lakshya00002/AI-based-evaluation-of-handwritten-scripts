from __future__ import annotations


def _band(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "mid"
    return "low"


def _top_items(items: list[str], n: int = 3) -> list[str]:
    return [x for x in items if x][:n]


def generate_feedback(
    *,
    student_keywords: list[str],
    reference_keywords: list[str],
    missing_concepts: list[str],
    keyword_score: float,
    semantic_score: float,
    grammar_score: float,
    coherence_score: float,
    relevance_score: float,
    final_score: float,
) -> dict[str, list[str] | str]:
    weak_areas: list[str] = []
    suggestions: list[str] = []
    strengths: list[str] = []

    student_kw_set = {k.lower().strip() for k in student_keywords if k.strip()}
    ref_kw_set = {k.lower().strip() for k in reference_keywords if k.strip()}
    matched_keywords = sorted(student_kw_set & ref_kw_set)
    missing_keywords = sorted(ref_kw_set - student_kw_set)

    if matched_keywords:
        strengths.append(f"Used relevant terminology: {', '.join(_top_items(matched_keywords, 4))}.")
    if semantic_score >= 0.7:
        strengths.append("Core explanation aligns well with the reference answer.")
    if coherence_score >= 0.65:
        strengths.append("Flow between ideas is reasonably coherent.")

    if missing_concepts:
        weak_areas.append(f"Concept coverage is incomplete ({len(missing_concepts)} key concept(s) missing).")
        suggestions.append(f"Add explicit discussion of: {', '.join(_top_items(missing_concepts, 5))}.")

    if grammar_score < 0.6:
        weak_areas.append("Grammar and sentence quality can be improved.")
        suggestions.append("Use shorter sentences and verify punctuation consistency.")

    if coherence_score < 0.6:
        weak_areas.append("Logical flow between points is weak.")
        suggestions.append("Link paragraphs using cause-effect transitions.")

    if relevance_score < 0.6:
        weak_areas.append("Answer is partially off-topic or incomplete.")
        suggestions.append("Map each paragraph directly to the question prompt.")

    if keyword_score < 0.5:
        weak_areas.append("Reference keywords are underused.")
        if missing_keywords:
            suggestions.append(f"Include keywords such as: {', '.join(_top_items(missing_keywords, 5))}.")

    if semantic_score < 0.5:
        weak_areas.append("Semantic alignment with the model answer is weak.")
        suggestions.append("Add the cause-effect chain from definition to outcome in 2-3 sentences.")

    if not suggestions:
        suggestions.append("Strong answer. Add one practical example to further strengthen depth.")

    score_band = _band(final_score)
    if score_band == "high":
        summary = "Strong submission with good coverage and alignment."
    elif score_band == "mid":
        summary = "Decent submission with partial coverage; targeted improvements can raise the grade."
    else:
        summary = "Foundational understanding is visible, but key gaps are reducing the score."

    return {
        "summary": summary,
        "strengths": strengths,
        "matched_keywords": _top_items(matched_keywords, 8),
        "missing_keywords": _top_items(missing_keywords, 8),
        "missing_concepts": missing_concepts,
        "weak_areas": weak_areas,
        "suggestions": suggestions,
    }

