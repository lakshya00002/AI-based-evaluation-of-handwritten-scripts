from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DeepAnalysisResult:
    concept_coverage_score: float
    context_accuracy_score: float
    coherence_score: float
    missing_concepts: list[str]


def _sentence_embeddings(texts: list[str]) -> list[list[float]]:
    vocab: dict[str, int] = {}
    tokenized: list[list[str]] = []
    for text in texts:
        tokens = re.findall(r"[A-Za-z0-9']+", text.lower())
        tokenized.append(tokens)
        for token in tokens:
            if token not in vocab:
                vocab[token] = len(vocab)

    vectors: list[list[float]] = []
    for tokens in tokenized:
        vec = [0.0] * len(vocab)
        for token in tokens:
            vec[vocab[token]] += 1.0
        vectors.append(vec)
    return vectors


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb + 1e-8)


def run_deep_analysis(
    student_text: str,
    reference_answer: str,
    reference_concepts: list[str],
) -> DeepAnalysisResult:
    embeddings = _sentence_embeddings([student_text, reference_answer] + reference_concepts)
    student_vec, reference_vec, *concept_vecs = embeddings
    context_accuracy = max(0.0, min(1.0, _cosine(student_vec, reference_vec)))

    covered, missing = 0, []
    for concept, concept_vec in zip(reference_concepts, concept_vecs):
        sim = _cosine(student_vec, concept_vec)
        if sim >= 0.38 or concept.lower() in student_text.lower():
            covered += 1
        else:
            missing.append(concept)
    concept_coverage = covered / (len(reference_concepts) or 1)

    sentences = [s.strip() for s in re.split(r"[.!?]+", student_text) if s.strip()]
    if len(sentences) <= 1:
        coherence = 0.6 if sentences else 0.0
    else:
        pair_scores: list[float] = []
        pair_vecs = _sentence_embeddings(sentences)
        for i in range(len(pair_vecs) - 1):
            pair_scores.append(max(0.0, _cosine(pair_vecs[i], pair_vecs[i + 1])))
        coherence = sum(pair_scores) / len(pair_scores)

    return DeepAnalysisResult(
        concept_coverage_score=max(0.0, min(1.0, concept_coverage)),
        context_accuracy_score=max(0.0, min(1.0, context_accuracy)),
        coherence_score=max(0.0, min(1.0, coherence)),
        missing_concepts=missing,
    )

