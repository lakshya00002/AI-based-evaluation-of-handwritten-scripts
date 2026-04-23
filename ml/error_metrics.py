from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class OCRErrorMetrics:
    cer: float | None
    wer: float | None
    reference_text: str | None
    extracted_text: str
    notes: list[str]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _levenshtein_distance(seq_a: list[str], seq_b: list[str]) -> int:
    if not seq_a:
        return len(seq_b)
    if not seq_b:
        return len(seq_a)
    dp = [[0] * (len(seq_b) + 1) for _ in range(len(seq_a) + 1)]
    for i in range(len(seq_a) + 1):
        dp[i][0] = i
    for j in range(len(seq_b) + 1):
        dp[0][j] = j
    for i in range(1, len(seq_a) + 1):
        for j in range(1, len(seq_b) + 1):
            cost = 0 if seq_a[i - 1] == seq_b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[-1][-1]


def compute_ocr_error_metrics(extracted_text: str, ground_truth_text: str | None) -> OCRErrorMetrics:
    cleaned_extracted = _normalize_text(extracted_text)
    if not ground_truth_text:
        return OCRErrorMetrics(
            cer=None,
            wer=None,
            reference_text=None,
            extracted_text=cleaned_extracted,
            notes=["Ground truth not provided; CER/WER skipped."],
        )

    cleaned_reference = _normalize_text(ground_truth_text)
    ref_chars = list(cleaned_reference)
    pred_chars = list(cleaned_extracted)
    char_distance = _levenshtein_distance(ref_chars, pred_chars)
    cer = char_distance / (len(ref_chars) or 1)

    ref_words = cleaned_reference.split()
    pred_words = cleaned_extracted.split()
    word_distance = _levenshtein_distance(ref_words, pred_words)
    wer = word_distance / (len(ref_words) or 1)

    return OCRErrorMetrics(
        cer=max(0.0, min(1.0, cer)),
        wer=max(0.0, min(1.0, wer)),
        reference_text=cleaned_reference,
        extracted_text=cleaned_extracted,
        notes=["CER/WER computed against provided OCR ground-truth text."],
    )
