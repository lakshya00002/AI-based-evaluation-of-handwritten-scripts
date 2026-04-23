from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass
class NLPAnalysisResult:
    tokens: list[str]
    pos_tags: list[tuple[str, str]]
    named_entities: list[tuple[str, str]]
    keywords: list[str]
    keyword_score: float
    bleu_score: float
    rouge_1_recall: float
    rouge_l_recall: float
    semantic_similarity_score: float
    semantic_similarity_method: str
    grammar_score: float
    structure_score: float
    length_normalization_score: float
    relevance_completeness_score: float


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text.lower())


def _ngram_counts(tokens: list[str], n: int) -> dict[tuple[str, ...], int]:
    counts: dict[tuple[str, ...], int] = {}
    if n <= 0 or len(tokens) < n:
        return counts
    for i in range(len(tokens) - n + 1):
        gram = tuple(tokens[i : i + n])
        counts[gram] = counts.get(gram, 0) + 1
    return counts


def _clipped_precision(candidate: list[str], reference: list[str], n: int) -> float:
    cand_counts = _ngram_counts(candidate, n)
    ref_counts = _ngram_counts(reference, n)
    if not cand_counts:
        return 0.0
    overlap = 0
    total = 0
    for gram, count in cand_counts.items():
        overlap += min(count, ref_counts.get(gram, 0))
        total += count
    return overlap / (total or 1)


def _bleu_score(student_text: str, reference_text: str, max_n: int = 4) -> float:
    candidate = _tokenize(student_text)
    reference = _tokenize(reference_text)
    if not candidate or not reference:
        return 0.0
    precisions: list[float] = []
    for n in range(1, max_n + 1):
        p = _clipped_precision(candidate, reference, n)
        precisions.append(max(p, 1e-9))
    geo_mean = math.exp(sum(math.log(p) for p in precisions) / max_n)
    c = len(candidate)
    r = len(reference)
    brevity_penalty = 1.0 if c > r else math.exp(1 - (r / (c or 1)))
    return max(0.0, min(1.0, brevity_penalty * geo_mean))


def _rouge_1_recall(student_text: str, reference_text: str) -> float:
    candidate = _tokenize(student_text)
    reference = _tokenize(reference_text)
    if not reference:
        return 0.0
    cand_counts = _ngram_counts(candidate, 1)
    ref_counts = _ngram_counts(reference, 1)
    overlap = 0
    for gram, count in ref_counts.items():
        overlap += min(count, cand_counts.get(gram, 0))
    return max(0.0, min(1.0, overlap / (len(reference) or 1)))


def _lcs_length(a: list[str], b: list[str]) -> int:
    if not a or not b:
        return 0
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def _rouge_l_recall(student_text: str, reference_text: str) -> float:
    candidate = _tokenize(student_text)
    reference = _tokenize(reference_text)
    if not reference:
        return 0.0
    lcs = _lcs_length(candidate, reference)
    return max(0.0, min(1.0, lcs / (len(reference) or 1)))


def _pos_tag(tokens: list[str]) -> list[tuple[str, str]]:
    tagged: list[tuple[str, str]] = []
    for token in tokens:
        if token.endswith("ing"):
            tag = "VBG"
        elif token.endswith("ed"):
            tag = "VBD"
        elif token.endswith("ly"):
            tag = "RB"
        elif token.endswith(("ion", "ment", "ness", "ity")):
            tag = "NN"
        elif token.endswith(("ive", "ous", "al", "able")):
            tag = "JJ"
        else:
            tag = "NN"
        tagged.append((token, tag))
    return tagged


def _ner(text: str) -> list[tuple[str, str]]:
    entities: list[tuple[str, str]] = []
    try:
        import spacy

        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
    except Exception:
        # simple fallback: uppercase chunks as pseudo entities
        entities = [(m.group(0), "MISC") for m in re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)]
    return entities


def _extract_keywords(text: str, top_n: int = 12) -> list[str]:
    tokens = [t for t in _tokenize(text) if len(t) > 3]
    freq: dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    ranked = sorted(freq.items(), key=lambda item: item[1], reverse=True)
    return [k for k, _ in ranked[:top_n]]


def _synonym_set(word: str) -> set[str]:
    synonyms = {word.lower()}
    static_map = {
        "ai": {"artificial intelligence"},
        "nlp": {"natural language processing"},
        "backpropagation": {"back propagation"},
        "gradient": {"derivative", "slope"},
        "weights": {"parameters"},
        "loss": {"error"},
    }
    synonyms.update(static_map.get(word.lower(), set()))
    return synonyms


def _keyword_score(student_keywords: list[str], reference_keywords: list[str]) -> float:
    if not reference_keywords:
        return 0.5
    matched = 0
    ref_sets = [_synonym_set(k) for k in reference_keywords]
    for student_kw in student_keywords:
        low = student_kw.lower()
        if any(low in ref_syns or ref_kw in _synonym_set(low) for ref_kw, ref_syns in zip(reference_keywords, ref_sets)):
            matched += 1
    return min(1.0, matched / max(1, len(reference_keywords)))


def _semantic_similarity(student_text: str, reference_text: str) -> float:
    score, _ = _semantic_similarity_with_method(student_text, reference_text)
    return score


def _semantic_similarity_with_method(student_text: str, reference_text: str) -> tuple[float, str]:
    s_text = student_text.strip()
    r_text = reference_text.strip()
    if not s_text or not r_text:
        return 0.0, "none"
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        vectors = model.encode([s_text, r_text], convert_to_numpy=True, normalize_embeddings=True)
        semantic = float((vectors[0] * vectors[1]).sum())
        return max(0.0, min(1.0, semantic)), "sentence-transformers(all-MiniLM-L6-v2)"
    except Exception:
        pass

    s_tokens = _tokenize(s_text)
    r_tokens = _tokenize(r_text)
    if not s_tokens or not r_tokens:
        return 0.0, "token-overlap-fallback"
    s_set, r_set = set(s_tokens), set(r_tokens)
    overlap = len(s_set & r_set)
    precision = overlap / len(s_set)
    recall = overlap / len(r_set)
    if precision + recall == 0:
        return 0.0, "token-overlap-fallback"
    return (2 * precision * recall) / (precision + recall), "token-overlap-fallback"


def _grammar_score(text: str) -> float:
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return 0.0
    proper_starts = sum(1 for s in sentences if s[0].isupper())
    avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
    punctuation_balance = 1.0 if text.count("(") == text.count(")") else 0.8
    length_score = 1.0 if 6 <= avg_len <= 30 else 0.7
    return max(0.0, min(1.0, (proper_starts / len(sentences)) * 0.5 + length_score * 0.3 + punctuation_balance * 0.2))


def _structure_score(text: str) -> float:
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return 0.0
    connectors = {"therefore", "because", "thus", "hence", "first", "second", "finally"}
    has_connector = 1.0 if any(word in _tokenize(text) for word in connectors) else 0.0
    sentence_variety = min(1.0, len(sentences) / 4.0)
    paragraph_like = 1.0 if "\n" in text else 0.7
    return max(0.0, min(1.0, 0.45 * sentence_variety + 0.35 * has_connector + 0.20 * paragraph_like))


def _length_normalization(student_text: str, reference_text: str) -> float:
    student_len = len(_tokenize(student_text))
    reference_len = len(_tokenize(reference_text))
    if reference_len == 0:
        return 0.0
    ratio = student_len / reference_len
    # Best when within +/-20% of expected answer length.
    if 0.8 <= ratio <= 1.2:
        return 1.0
    if ratio < 0.8:
        return max(0.0, ratio / 0.8)
    return max(0.0, min(1.0, 1.2 / ratio))


def _relevance_completeness(student_text: str, question_text: str, reference_keywords: list[str]) -> float:
    s_tokens = set(_tokenize(student_text))
    q_tokens = set(_tokenize(question_text))
    topic_overlap = len(s_tokens & q_tokens) / (len(q_tokens) or 1)
    keyword_coverage = len({k for k in reference_keywords if k.lower() in student_text.lower()}) / (len(reference_keywords) or 1)
    return max(0.0, min(1.0, 0.5 * topic_overlap + 0.5 * keyword_coverage))


def run_nlp_analysis(
    student_text: str,
    reference_answer: str,
    reference_keywords: list[str],
    question_text: str,
) -> NLPAnalysisResult:
    tokens = _tokenize(student_text)
    pos_tags = _pos_tag(tokens)
    keywords = _extract_keywords(student_text)
    entities = _ner(student_text)
    keyword_score = _keyword_score(keywords, reference_keywords)
    bleu = _bleu_score(student_text, reference_answer)
    rouge_1 = _rouge_1_recall(student_text, reference_answer)
    rouge_l = _rouge_l_recall(student_text, reference_answer)
    semantic_score, semantic_method = _semantic_similarity_with_method(student_text, reference_answer)
    grammar_score = _grammar_score(student_text)
    structure_score = _structure_score(student_text)
    length_norm = _length_normalization(student_text, reference_answer)
    relevance_score = _relevance_completeness(student_text, question_text, reference_keywords)
    return NLPAnalysisResult(
        tokens=tokens,
        pos_tags=pos_tags,
        named_entities=entities,
        keywords=keywords,
        keyword_score=keyword_score,
        bleu_score=bleu,
        rouge_1_recall=rouge_1,
        rouge_l_recall=rouge_l,
        semantic_similarity_score=semantic_score,
        semantic_similarity_method=semantic_method,
        grammar_score=grammar_score,
        structure_score=structure_score,
        length_normalization_score=length_norm,
        relevance_completeness_score=relevance_score,
    )

