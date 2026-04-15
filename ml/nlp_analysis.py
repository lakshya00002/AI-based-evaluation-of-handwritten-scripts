from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class NLPAnalysisResult:
    tokens: list[str]
    pos_tags: list[tuple[str, str]]
    named_entities: list[tuple[str, str]]
    keywords: list[str]
    keyword_score: float
    semantic_similarity_score: float
    grammar_score: float
    relevance_completeness_score: float


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text.lower())


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
    s_text = student_text.strip()
    r_text = reference_text.strip()
    if not s_text or not r_text:
        return 0.0
    s_tokens = _tokenize(s_text)
    r_tokens = _tokenize(r_text)
    if not s_tokens or not r_tokens:
        return 0.0
    s_set, r_set = set(s_tokens), set(r_tokens)
    overlap = len(s_set & r_set)
    precision = overlap / len(s_set)
    recall = overlap / len(r_set)
    if precision + recall == 0:
        return 0.0
    return (2 * precision * recall) / (precision + recall)


def _grammar_score(text: str) -> float:
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return 0.0
    proper_starts = sum(1 for s in sentences if s[0].isupper())
    avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
    punctuation_balance = 1.0 if text.count("(") == text.count(")") else 0.8
    length_score = 1.0 if 6 <= avg_len <= 30 else 0.7
    return max(0.0, min(1.0, (proper_starts / len(sentences)) * 0.5 + length_score * 0.3 + punctuation_balance * 0.2))


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
    semantic_score = _semantic_similarity(student_text, reference_answer)
    grammar_score = _grammar_score(student_text)
    relevance_score = _relevance_completeness(student_text, question_text, reference_keywords)
    return NLPAnalysisResult(
        tokens=tokens,
        pos_tags=pos_tags,
        named_entities=entities,
        keywords=keywords,
        keyword_score=keyword_score,
        semantic_similarity_score=semantic_score,
        grammar_score=grammar_score,
        relevance_completeness_score=relevance_score,
    )

